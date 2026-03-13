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

from backend.utils import _extract_yt_id

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
    
    def extract_metadata(self, local_file_path: str, video_id: str) -> Dict[str, Any]:
        """Extracts metadata from the video file."""
        try:
            return self._metadata_from_yt_dlp(video_id)
        except Exception as e:
            logger.warning(f"yt-dlp metadata extraction failed: {e}. Falling back to ffprobe.")
            return self._metadata_from_ffprobe(local_file_path)

    def extract_transcript(self, local_file_path: str, video_id: str) -> str:
        """Extracts transcript using yt-dlp captions or falls back to Whisper."""
        try:
            transcript = self._transcript_from_yt_dlp(video_id)
            if transcript:
                logger.info("Transcript extracted from YouTube captions.")
                return transcript
        except Exception as e:
            logger.warning(f"yt-dlp transcript extraction failed: {e}. Falling back to Whisper.")

        logger.info("Extracting transcript using Whisper...")
        return self._transcript_from_whisper(local_file_path)
    
    def extract_ocr(self, local_file_path: str) -> List[str]:
        """Extracts OCR text from video frames."""
        frames_dir = Path(DOWNLOAD_DIR) / "frames" / Path(local_file_path).stem
        frames_dir.mkdir(parents=True, exist_ok=True)

        frame_pattern = str(frames_dir / "frame_%04d.jpg")
        cmd = [
            "ffmpeg", 
            "-y", "-loglevel", "error",  
            "-i", local_file_path,       
            "-vf", f"fps=1/{FRAME_SAMPLING_RATE}",
            "-q:v", "2",
            frame_pattern,              
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr}")
        
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))
        ocr_texts = []
        for frame in frame_files:
            text = self._run_tesseract(str(frame))
            ocr_texts.append(text)

        return ocr_texts

# ─── Private Helpers Functions ────────────────────────────────────────────────────────
    def _metadata_from_yt_dlp(self, video_id: str) -> Dict[str, Any]:
        """Extracts metadata using yt-dlp."""
        import json
        url = f"https://www.youtube.com/watch?v={video_id}"
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp metadata extraction failed: {result.stderr}")
        
        metadata = json.loads(result.stdout)
        return {
            "title": metadata.get("title"),
            "channel": metadata.get("uploader"),
            "duration": metadata.get("duration"),
            "upload_date": metadata.get("upload_date"),
            "view_count": metadata.get("view_count"),
            "description": metadata.get("description", "")[:2000],  
            "categories": metadata.get("categories", []),
            "tags": metadata.get("tags", []),
        }

    def _metadata_from_ffprobe(self, local_file_path: str) -> Dict[str, Any]:
        """ffprobe when yt-dlp metadata extraction is unavailable."""
        import json
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", 
                "-print_format", "json",
                "-show_format", "-show_streams", 
                local_file_path
            ],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        raw_metadata = json.loads(result.stdout)
        fmt = raw_metadata.get("format", {})
        return {
            "title": fmt.get("tags", {}).get("title"),
            "channel": fmt.get("tags", {}).get("artist"),
            "duration": fmt.get("duration"),
            "upload_date": fmt.get("tags", {}).get("creation_time"),
            "view_count": fmt.get("tags", {}).get("view_count"),
        }
    
    def _transcript_from_whisper(self, local_file_path: str) -> str:
        """Extracts transcript using OpenAI Whisper."""
        import whisper
        model = whisper.load_model("base")

        result = model.transcribe(local_file_path, fp16=False)
        return result.get("text", "")

    def _run_tesseract(self, image_path: str) -> str:
        """Runs Tesseract OCR on the given image."""
        result = subprocess.run(
            ["tesseract", image_path, "stdout"],
            capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    
    def _transcript_from_yt_dlp(self, video_id: str) -> str:
        """Extracts transcript using yt-dlp captions."""
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id)

            transcript = ""
            for snippet in fetched_transcript:
                transcript += snippet.text + " "
            
            return transcript.strip()

        except Exception as e:
            logger.warning(f"YouTubeTranscriptApi failed: {e}")
            return ""  

# Example usage:
if __name__ == "__main__":
    vi_service = VideoIndexerService()
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    try:
        local_path, video_id = vi_service.download_youtube_video(test_url)
        logger.info(f"Downloaded video saved to: {local_path} with ID: {video_id}")

        metadata = vi_service.extract_metadata(local_path, video_id)
        logger.info(f"Extracted metadata")

        transcript = vi_service.extract_transcript(local_path, video_id)
        logger.info(f"Extracted transcript")

        import pdb; pdb.set_trace()  

        ocr_text = vi_service.extract_ocr(local_path)

        logger.info(f"Extracted OCR text from frames: {ocr_text[:3]}")  # log first 3 frames' OCR

        # Clean up
        os.remove(local_path)

        logger.info("Video indexing complete.")

        print(ocr_text[:3])  # print first 3 frames' OCR for quick verification
    except Exception as e:
        logger.error(f"Error downloading video: {e}")