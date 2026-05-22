"""This module contains utility functions for raw text splitting"""
from abc import ABC, abstractmethod
from config import OPENAI_API_KEY

from langchain_text_splitters import RecursiveCharacterTextSplitter

class ChunkingStrategy(ABC):
    @abstractmethod
    def split(self, text)->list[str]:
        """Split raw text into chunks"""
        pass


class RecursiveCharacterChunkingStrategy(ChunkingStrategy):
    """Implements the Recursive Character Text Splitter strategy"""
    def __init__(self):
        self._splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=500,
            chunk_overlap=50,
        )

    def split(self, text) -> list[str]:
        """Split raw text into chunks using the Recursive Character Text Splitter strategy"""
        return self._splitter.split_text(text)


class TextSplitter:
    """Class responsible for splitting raw text into chunks using a specified chunking strategy."""
    def __init__(self, strategy: ChunkingStrategy):
        self.strategy = strategy

    @property
    def strategy(self)->ChunkingStrategy:
        """Set the chunking strategy"""
        return self._strategy
    
    @strategy.setter
    def strategy(self, strategy: ChunkingStrategy):
        self._strategy = strategy

    def create_chunks(self, text: str) -> list[str]:
        """Create chunks from raw text using the specified chunking strategy."""
        return self._strategy.split(text)
    
    def create_chunks_with_metadata(self, text: str, metadata: dict) -> list[dict]:
        """Create chunks from raw text and attach metadata to each chunk."""
        chunks = self._strategy.split(text)
        return [{"chunk": chunk, "metadata": metadata} for chunk in chunks]
