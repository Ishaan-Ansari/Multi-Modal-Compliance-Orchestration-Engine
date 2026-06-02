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
        self.collection = self.client.get_or_create_collection(collection_name)
        logger.info(f"Connected to ChromaDB at {chroma_host}:8000, using collection '{collection_name}'")

    def add_documents(self, documents: List[Dict[str, str]], embeddings: List[List[float]]) -> None:
        """Add documents to the vector database."""
        if not documents:
            logger.warning("No documents or embeddings provided.")
            return
        
        if embeddings is None or len(embeddings) != len(documents):
            raise ValueError("Embeddings list must be the same length as documents list.")
        
        try:
            ids = [str(uuid.uuid4()) for _ in documents]
            metadatas = [{"source": doc.get("source", "unknown")} for doc in documents]

            texts = [doc.get("text", "") for doc in documents]

            add_kwargs = dict(ids=ids, metadatas=metadatas, documents=texts, embeddings=embeddings)
            if embeddings is not None:
                add_kwargs["embeddings"] = embeddings
                
            self.collection.add(**add_kwargs)
            logger.info(f"Added {len(documents)} documents to the vector database.")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise e
        
    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, str]]:
        """Query the vector database for similar documents."""
        try:
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
            return results.get("documents", [])
        except Exception as e:
            logger.error(f"Error querying vector database: {e}")
            raise e
        