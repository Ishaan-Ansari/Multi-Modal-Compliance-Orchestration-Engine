import os
import re
import json
from openai import OpenAI, AsyncOpenAI
from config import OPENAI_API_KEY
from typing import Any, Dict, List
from logger import loggerNodes as logger


from langchain_core.messages import SystemMessage, HumanMessage
from backend.src.graph.state import VideoAuditState, ComplianceIssue

from backend.scripts.vector_database import VectorDatabase
from backend.scripts.embeddings import Embeddings

from backend.src.services.video_indexer import VideoIndexerService
from sentence_transformers import CrossEncoder

openai_client = OpenAI(api_key=OPENAI_API_KEY)
async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_reranker = None

def get_reranker()->CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("Loading CrossEncoder model for compliance issue reranking...")
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker

def rerank(query: str, docs: list, top_k: int = 5)->list:
    """
    Score each (query, doc) pair with a cross-encoder.
    Returns the top_k docs sorted by relevance to the query.
    """
    if not docs:
        return []
    
    pairs = [(query, doc.content) for doc in docs]
    scores = get_reranker().predict(pairs)

    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored_docs[:top_k]]

def extract_claims(transcript: str, ocr_text: str, llm)->List[str]:
    """
    Extract 3-5 specific, checkable claims to improve retrieval targeting.
    Falls back to a truncated transcript if parsing fails.
    """
    extraction_prompt = f"""
    You are a compliance pre-screener.
    Extract 3-5 specific, checkable claims from the video that should be validated against compliance rules.

    Focus on:
    - health claims
    - pricing claims
    - comparative claims
    - testimonials/endorsements
    - CTA and urgency language
    - disclosures

    Return ONLY a JSON array of strings.

    TRANSCRIPT:
    {transcript[:3000]}

    ON-SCREEN TEXT:
    {' '.join(ocr_text[:20])}
    """
    try:
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        claims = json.loads(response.content)
        if isinstance(claims, list) and claims:
            return [str(c).strip() for c in claims[:5] if str(c).strip()]
    except Exception as e:
        logger.warning(f"Claim extraction failed: {e}. Falling back to transcript chunking.")
    
    # Fallback: simple heuristic extraction from transcript
    fallback = transcript[:500].strip()
    return [fallback] if fallback else []

def index_video_node(state: VideoAuditState)->Dict[str, Any]:
    """
    Downloads the video from URL,
    Uploads to the cloud storage,
    Extracts metadata, transcript, and OCR text,
    """
    video_url = state.get("video_url")
    video_id_input = state.get("video_id")

    logger.info(f"Starting video indexing for video URL: {video_url}")

    local_filename = "test_video.mp4" # placeholder for testing

    try:
        video_indexer = VideoIndexerService()
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_file_path, video_id = video_indexer.download_youtube_video(video_url, video_id_input)
            metadata = video_indexer.extract_metadata(local_file_path, video_id)
        else:
            raise ValueError(f"Unsupported video URL: {video_url}")
        
        logger.info("Exctracting transcript...")

        transcript = video_indexer.extract_transcript(local_file_path, video_id)

        ocr_text = video_indexer.extract_ocr(local_file_path, video_id)

        # Clean up local file after processing       
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
            logger.info(f"Removed local file: {local_file_path}")

        return {
                "video_id": video_id,
                "local_file_path": local_file_path,
                "video_metadata": metadata,
                "transcript": transcript,
                "ocr_text": ocr_text,
                "errors": [],
            }

    except Exception as e:
        error_msg = f"Error in video indexing: {str(e)}"
        logger.error(error_msg)
        return {
            "errors": [error_msg],
            "compliance_results": []
        }

def compliance_audit_node(state: VideoAuditState)->Dict[str, Any]:
    """
    This node performs retrieval augmented generation to audit the content of the video for compliance issues. 

    RAG-based compliance audit:
    1) claim extraction
    2) hybrid candidate retrieval
    3) cross-encoder reranking
    4) LLM audit generation
    """
    logger.info(f"----[Node: compliance_audit_node] querying knowledge base for compliance audit----")

    transcript = state.get("transcript", "")
    if not transcript:
        logger.warning("No transcript available for compliance audit.")
        return {
            "final_status": "failed",
            "final_report": "Compliance audit failed: no transcript available.",
            "retrieved_contexts": [],
        }
    
    # RAG retrieval

    # Step A: Build retrieval claims from the transcript and OCR text. We concatenate the transcript and OCR text to create a single query string that represents the content of the video. This query will be used to search for relevant documents in the vector store.
    ocr_text = state.get("ocr_text", [])
    query_text = f"{transcript} {' '.join(ocr_text)}"
    claims = extract_claims(transcript, ocr_text, state.get("llm"))
    if not claims:
        logger.warning("No claims extracted for retrieval. Using fallback query.")
        claims = [query_text[:500]]  # Fallback to truncated transcript as a single claim

    ## Perform similarity search in the vector store to retrieve relevant documents based on the transcript and OCR text. K=3 means we want to retrieve the top 3 most relevant documents.
    # docs = vector_store.similarity_search(query_text, k=3)

    # Step B: Hybrid retrieval - we perform two separate retrievals, one using the full query text and another using the extracted claims. We then combine the results to create a more comprehensive set of candidate documents for the compliance audit.
    
    all_docs = []
    for claim in claims:
        retrieved = vector_store.similarity_search(
            claim,
            k=5
        )
        all_docs.extend(retrieved)

    # Fallback if claim-wise retrieval returns no results
    if not all_docs:
        logger.warning("Claim-wise retrieval returned no results. Falling back to query-based retrieval.")
        all_docs = vector_store.similarity_search(
            query_text,
            k=5
        )

    # deduplicate retrieved documents
    seen_ids = set()
    unique_docs = []
    for doc in all_docs:
        doc_id = doc.metadata.get("id")
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
            unique_docs.append(doc)

    # Step C: Rerank the retrieved documents using a cross-encoder to prioritize the most relevant ones for the compliance audit.
    rerank_queries = f"Brand compliance rules relevant toL {' | '.join(claims)}"
    try:
        top_docs = rerank(rerank_queries, unique_docs, top_k=5)
        if not top_docs:
            logger.warning("Reranking returned no results. Using original retrieved documents.")
            top_docs = unique_docs[:5]  
    except Exception as e:
        logger.error(f"Error during reranking: {e}. Using original retrieved documents.")
        top_docs = unique_docs[:5]

    # Build context list from top_docs
    retrieved_contexts = [doc.page_content for doc in top_docs if getattr(doc, "page_content", "").strip()]
    retrieved_rules = "\n\n".join(retrieved_contexts)


    system_prompt = f"""
    You are a senior brand compliance auditor.
    OFFICIAL REGULATORY RULES:
    {retrieved_rules}
    INSTRUCTIONS:
    1. Analyze the Transcript and OCR text below.
    2. Identify ANY violations of the rules.
    3. Return strictly JSON in the following format:
    {{
    "compliance_results": [
        {{
        "category": "Claim Validation",
        "severity": "CRITICAL",
        "description": "Explanation of the violation..."
        }}
    ],
    "status": "FAIL",
    "final_report": "Summary of findings..."
    }}

    If no violations are found, set "status" to "PASS" and "compliance_results" to [].
    """

    user_message = f"""
    VIDEO_METADATA : {state.get('video_metadata',{})}
    TRANSCRIPT : {transcript}
    ON-SCREEN TEXT (OCR) : {ocr_text}
    """

    try:
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
        content = response.content

        # The LLM might return the JSON wrapped in markdown code blocks, so we need to extract the JSON string from the response content before parsing it.
        if "```" in content:
            content = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL).group(1)

        audit_data = json.loads(content.strip())


        return {
            "compliance_results": audit_data.get("compliance_results", []),
            "final_status": audit_data.get("status", "FAIL"),
            "final_report": audit_data.get("final_report", ""),
            "retrieved_contexts": [doc.metadata for doc in retrieved],  # include metadata of retrieved docs for transparency
        }
    except Exception as e:
        logger.error(f"Error during compliance audit generation: {e}")
        return {
            "compliance_results": [],
            "final_status": "failed",
            "final_report": f"Compliance audit failed due to error: {str(e)}",
            "retrieved_contexts": [doc.metadata for doc in retrieved],
        }
