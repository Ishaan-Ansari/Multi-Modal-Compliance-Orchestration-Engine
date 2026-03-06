"""
VideoIndexerService
===================
- Youtube video downloading using yt-dlp
- Metadata extraction
- Transcript extraction (Youtube captions -> whisper fallback)
- OCR via frame sampling + Tesseract
"""

import os
import re
import uuid
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from logger import loggerServices as logger

DOWNLOAD_DIR = os.getenv("VIDEO_DOWNLOAD_DIR", "tmp/video_audit_downloads")
FRAME_SAMPLING_RATE = int(os.getenv("OCR_FRAME_SAMPLING_RATE", "30")) # every N seconds

class VideoIndexerService:
    def __init__(self):
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def download_youtube_video(
            self,
            url: str,
            video_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Downloads a YouTube video and returns the local file path and video ID."""
        logger.info(f"Downloading YouTube video: {url}")
        
        video_id = video_id or _extract_yt_id(url) or str(uuid.uuid4())
        output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

        cmd = [
            "yt-dlp",
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "--output", output_path,
            "--no-playlist",
            "--quiet",
            url,
        ]
        logger.info(f"[VideoIndexer] Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed with code {result.returncode}: {result.stderr}"
            )
        
        # Resolve the actual file path (extension may vary)
        matches = list(Path(DOWNLOAD_DIR).glob(f"{video_id}.*"))
        if not matches:
            raise FileNotFoundError(
                f"Download completed but file not found for id={video_id}"
            )
        
        local_file_path = str(matches[0])
        logger.info(f"[VideoIndexer] Downloaded -> {local_file_path}")

        return local_file_path, video_id
    
    



# ─── Utility ─────────────────────────────────────────────────────────────────
def _extract_yt_id(url: str) -> Optional[str]:
    """Extracts the YouTube video ID from various URL formats."""
    patterns = [
        r"youtu\.be/([^?&]+)",  # youtu.be/VIDEOID
        r"youtube\.com/watch\?v=([^?&]+)",  # youtube.com/watch?v=VIDEOID
        r"youtube\.com/embed/([^?&]+)",  # youtube.com/embed/VIDEOID
        r"youtube\.com/v/([^?&]+)",  # youtube.com/v/VIDEOID
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", # v=VIDEOID
        r"shorts/([A-Za-z0-9_-]{11})", # youtube.com/shorts/VIDEOID

    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Example usage:
if __name__ == "__main__":
    vi_service = VideoIndexerService()
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    try:
        local_path, video_id = vi_service.download_youtube_video(test_url)
        logger.info(f"Downloaded video saved to: {local_path} with ID: {video_id}")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")