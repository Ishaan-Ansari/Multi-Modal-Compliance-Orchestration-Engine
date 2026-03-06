import os
import re
import json
from typing import Any, Dict, List
from logger import loggerNodes as logger

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

    