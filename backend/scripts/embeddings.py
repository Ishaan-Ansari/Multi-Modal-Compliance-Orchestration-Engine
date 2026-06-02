from typing import List

from backend.utils import get_openai_embeddings, get_openai_embeddings_async

class Embeddings:
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return get_openai_embeddings(texts)