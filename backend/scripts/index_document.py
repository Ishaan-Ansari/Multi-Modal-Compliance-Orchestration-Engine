"""This module is responsible for indexing documents into the vector database."""
import os
import glob
from dotenv import load_dotenv
load_dotenv()

from backend.scripts.text_splitter import TextSplitter, RecursiveCharacterChunkingStrategy
from backend.scripts.vector_database import VectorDatabase
from backend.scripts.embeddings import Embeddings

from logger import loggerIndexing as logger


def index_documents():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "../../backend/data")
        vector_db = VectorDatabase()

        text_splitter = TextSplitter(strategy=RecursiveCharacterChunkingStrategy())
        embeddings = Embeddings()

        for file in glob.glob(os.path.join(data_dir, "*.txt")):
            with open(file, "r") as f:
                text = f.read()

                chunks = text_splitter.create_chunks(text)

                if not chunks:
                    logger.warning(f"No chunks created for file: {file}")
                    continue

                embeddings_list = embeddings.get_embeddings(chunks)
                source_name = os.path.basename(file)
                documents = [
                    {"text": chunk, "source": source_name} 
                    for chunk in chunks    
                ]
                vector_db.add_documents(documents, embeddings_list)
        logger.info("Document indexing completed successfully.")
    except Exception as e:
        logger.error(f"Error during document indexing: {e}")
        raise e