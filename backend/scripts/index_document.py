"""This module is responsible for indexing documents into the vector database."""
import os
import glob
from dotenv import load_dotenv
load_dotenv()

from backend.scripts.text_splitter import TextSplitter, RecursiveCharacterChunkingStrategy
from backend.scripts.vector_database import VectorDatabase
from backend.scripts.embeddings import Embeddings

from backend.utils import extract_text_from_pdf

from logger import loggerIndexing as logger


def index_documents():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "../../backend/data")
        vector_db = VectorDatabase()

        text_splitter = TextSplitter(strategy=RecursiveCharacterChunkingStrategy())
        embeddings = Embeddings()

        pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found in the data directory.")
            return
        
        for file in pdf_files:
            source_name = os.path.basename(file)

            logger.info(f"Processing file: {file}")
            text = extract_text_from_pdf(file)

            if not text.strip():
                logger.warning(f"No text extracted from file: {file}")
                continue
                
            # Split the text into chunks and generate embeddings
            chunks = text_splitter.create_chunks(text)

            if not chunks:
                logger.warning(f"No chunks created for file: {file}")
                continue
            
            # Generate embeddings for the chunks and add them to the vector database
            embeddings_list = embeddings.get_embeddings(chunks)

            # Add documents to the vector database with source metadata
            source_name = os.path.basename(file)
            documents = [
                {"text": chunk, "source": source_name} 
                for chunk in chunks    
            ]
            vector_db.add_documents(documents, embeddings=embeddings_list)
        logger.info("Document indexing completed successfully.")
    except Exception as e:
        logger.error(f"Error during document indexing: {e}")
        raise e