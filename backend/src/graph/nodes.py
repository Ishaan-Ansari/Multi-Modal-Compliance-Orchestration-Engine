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
    except Exception as e:
        error_msg = f"Error in video indexing: {str(e)}"
        logger.error(error_msg)
        return {
            "errors": [error_msg],
            "compliance_results": []
        }
        

    