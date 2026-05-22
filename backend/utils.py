"""This module contains utility functions"""

import re
from typing import List, Optional

from openai import OpenAI, AsyncOpenAI
from config import OPENAI_API_KEY
from constants import DEFAULT_OPENAI_EMBEDDING_MODEL

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
OPENAI_ASYNC_CLIENT = AsyncOpenAI(api_key=OPENAI_API_KEY)

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

def get_openai_embeddings(texts: List[str], batch_size=2000) -> List[List[float]]:
    """Returns the default OpenAI embedding model."""
    if not isinstance(texts, list):
        raise ValueError("texts must be a list")
    
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)] 
    embeddings = []
    for batch in batches:
        response = OPENAI_CLIENT.embeddings.create(
            input=batch,
            model=DEFAULT_OPENAI_EMBEDDING_MODEL
        )
        _embeddings = [item.embedding for item in response.data]
        embeddings.extend(_embeddings)
    return embeddings

async def get_openai_embeddings_async(texts: List[str], batch_size=2000) -> List[List[float]]:
    """Returns the default OpenAI embedding model asynchronously."""
    if not isinstance(texts, list):
        raise ValueError("texts must be a list")
    
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)] 
    embeddings = []
    for batch in batches:
        response = await OPENAI_ASYNC_CLIENT.embeddings.create(
            input=batch,
            model=DEFAULT_OPENAI_EMBEDDING_MODEL
        )
        _embeddings = [item.embedding for item in response.data]
        embeddings.extend(_embeddings)
    return embeddings