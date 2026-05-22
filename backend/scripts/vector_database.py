"""This module contains utilities for setting up and interacting with the vector database."""
import os
import asyncio
import uuid
import chromadb
from typing import List, Dict, Optional

from logger import loggerVectorDB as logger

class VectorDatabase:
    def __init__(self, collection_name: str = "db_collection"):
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.client = chromadb.HttpClient(host=chroma_host, port=8000)

        self.collection_name = collection_name
        self.collection = self._get_or_create_collection(collection_name)

    def add_documents(self, documents: List[Dict[str, str]]) -> None:
        """Add documents to the vector database."""
        try:
            ids = [str(uuid.uuid4()) for _ in documents]
            metadatas = [{"source": doc.get("source", "unknown")} for doc in documents]
            self.collection.add(ids=ids, metadatas=metadatas, documents=documents)
            logger.info(f"Added {len(documents)} documents to the vector database.")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise e
        
        