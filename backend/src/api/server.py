import uuid        
import logging     
from fastapi import FastAPI, HTTPException  

from pydantic import BaseModel  
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from backend.src.api.telemetry import setup_telemetry
setup_telemetry()

# Import workflow graph
from backend.src.graph.workflow import app as compliance_graph

from logger import loggerServer as logger

app = FastAPI()

class AuditRequest(BaseModel):
    """
    Defines the expected structure of incoming API requests.
    
    Pydantic validates that:
    - The request contains a 'video_url' field
    - The value is a string (not int, list, etc.)
    """
    video_url: str  

class ComplianceIssue(BaseModel):
    category: str
    severity: str
    description: str

class AuditResponse(BaseModel):
    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_results: List[ComplianceIssue]

@app.post("/audit", response_model=AuditResponse)
async def audit_video(audit_request: AuditRequest):
    """
    This endpoint triggers the process
    1. Generate unique session ID
    2. Prepare input for LangGraph workflow
    3. Invoke the graph (Indexer → Auditor)
    4. Return formatted results
    """
    session_id = str(uuid.uuid4())
    logger.info(f"Received audit request for video URL: {audit_request.video_url} | Session ID: {session_id}")

    # Prepare input for the graph
    graph_input = {
        "video_url": audit_request.video_url,
        "session_id": session_id
    }

    try:
        # Invoke the LangGraph workflow
        graph_output = compliance_graph.run(graph_input)

        # Format the response
        response = AuditResponse(
            session_id=session_id,
            video_id=graph_output.get("video_id", ""),
            status="completed",
            final_report=graph_output.get("final_report", ""),
            compliance_results=[
                ComplianceIssue(**issue) for issue in graph_output.get("compliance_results", [])
            ]
        )
        return response

    except Exception as e:
        logger.error(f"Error processing audit request: {str(e)} | Session ID: {session_id}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the audit request.")

@app.get("/health")
def health_check():
    """
    Endpoint to verify the API is running.
    """
    return {"status": "healthy", "service": "Brand Guardian AI"}