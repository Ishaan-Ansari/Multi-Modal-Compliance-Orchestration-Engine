"""This module contains utility functions"""

import re
from typing import Optional

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
