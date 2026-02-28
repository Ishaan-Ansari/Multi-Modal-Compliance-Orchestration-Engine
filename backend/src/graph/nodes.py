import json
import os
from logger import loggerNodes as logger
import re
from typing import Any, Dict, List

from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from backend.src.graph.state import VideoAuditState, ComplianceIssue

from backend.src.services.video_indexer import VideoIndexerService

def index_video_node(state: VideoAuditState)->Dict[str, Any]:
    """
    Downloads the video from URL,
    Uploads to the cloud storage,
    Extracts metadata, transcript, and OCR text,
    """
    video_url = state.get("video_url")
    video_id_input = state.get("video_id")

    logger.info(f"Starting video indexing for video URL: {video_url}")

    