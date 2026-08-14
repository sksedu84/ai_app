"""
Vector database and embedding utilities for the RAG pipeline.

This module handles document ingestion, chunking, embedding, and vector storage.
Uses PostgreSQL with pgvector for production-grade vector storage.
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.documents import Document
from sqlalchemy import create_engine, text

from common import constants
from config.logger import Logger
from config.database import DatabaseConfig

logger = Logger.get_logger()


class VectorDatabaseManager:
    """Manages vector database operations for document embeddings using PostgreSQL with pgvector."""

    # Collection/table name
    COLLECTION_NAME: str = "documents"
    
    def __init__(self):
        """Initialize the vector database manager with PostgreSQL pgvector."""
        self.embeddings = OllamaEmbeddings(
            model=constants.EMBEDDING_MODEL,
            base_url="http://localhost:11434"  # Default Ollama URL
        )
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize the vector database connection with pgvector."""
        try:
            connection_string = DatabaseConfig.psycopg2_db_con_as_string()

            # Test connection
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Initialize PGVector store
            self.db = PGVector(
                collection_name=self.COLLECTION_NAME,
                connection_string=connection_string,
                embedding_function=self.embeddings
            )

            logger.info("PostgreSQL pgvector database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            raise
    
    @staticmethod
    def _get_file_hash(file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def _load_documents(document_dir: str) -> List[Document]:
        """
        Load documents from the specified directory.
        
        Args:
            document_dir: Path to document directory
            
        Returns:
            List of loaded documents
        """
        docs = []
        doc_path = Path(document_dir)
        
        if not doc_path.exists():
            logger.warning(f"Document directory does not exist: {document_dir}")
            return docs
        
        try:
            # Load text files
            txt_loader = DirectoryLoader(
                str(doc_path),
                glob="**/*.txt",
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs.extend(txt_loader.load())
            logger.info(f"Loaded {len(txt_loader.load())} text documents")
        except Exception as e:
            logger.error(f"Error loading text documents: {e}")
        
        try:
            # Load PDF files
            pdf_loader = DirectoryLoader(
                str(doc_path),
                glob="**/*.pdf",
                loader_cls=PyPDFLoader
            )
            docs.extend(pdf_loader.load())
            logger.info(f"Loaded PDF documents")
        except Exception as e:
            logger.error(f"Error loading PDF documents: {e}")
        
        try:
            # Load DOCX files
            docx_loader = DirectoryLoader(
                str(doc_path),
                glob="**/*.docx",
                loader_cls=Docx2txtLoader
            )
            docs.extend(docx_loader.load())
            logger.info(f"Loaded DOCX documents")
        except Exception as e:
            logger.error(f"Error loading DOCX documents: {e}")
        
        logger.info(f"Total documents loaded: {len(docs)}")
        return docs
    
    @staticmethod
    def _chunk_documents(documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks with overlap.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=constants.CHUNK_SIZE,
            chunk_overlap=constants.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_documents(documents)
        logger.info(f"Documents split into {len(chunks)} chunks")
        
        # Add chunk metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata[constants.CHUNK_INDEX] = idx
        
        return chunks
    
    def _should_reindex_document(self, file_path: Path) -> bool:
        """
        Determine if a document needs to be re indexed.
        
        Args:
            file_path: Path to the document
            
        Returns:
            True if the document should be re indexed, False otherwise
        """
        try:
            file_hash = self._get_file_hash(file_path)
            # Query existing metadata for this file
            results = self.db.get(
                where={constants.SOURCE_FILE: str(file_path)}
            )
            
            if results and len(results.get("ids", [])) > 0:
                # Check if hash matches
                stored_hashes = results.get("metadatas", [])
                if stored_hashes and stored_hashes[0].get(constants.FILE_HASH) == file_hash:
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Could not check if document needs reindexing: {e}")
            return True
    
    def ingest_documents(self, document_dir: str = constants.DOCUMENT_DATA_DIR) -> Dict[str, Any]:
        """
        Ingest documents from a directory into a vector database.
        
        Args:
            document_dir: Path to document directory
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting document ingestion from {document_dir}")
        
        try:
            # Load documents
            documents = self._load_documents(document_dir)
            if not documents:
                logger.warning("No documents found to ingest")
                return {
                    "status": constants.OK,
                    "message": "No documents found",
                    "added_chunks": 0,
                    "added_files": 0
                }
            
            # Chunk documents
            chunks = self._chunk_documents(documents)
            
            # Add metadata to chunks
            for chunk in chunks:
                chunk.metadata[constants.FILE_HASH] = self._get_file_hash(
                    Path(chunk.metadata.get("source", ""))
                )
            
            # Add chunks to vector database
            try:
                self.db.add_documents(chunks)
                logger.info(f"Successfully ingested {len(chunks)} chunks from {len(documents)} documents")
            except Exception as add_error:
                logger.error(f"Error adding documents to PGVector: {add_error}")
                raise

            return {
                "status": constants.OK,
                "message": "Documents ingested successfully",
                "added_chunks": len(chunks),
                "added_files": len(set(c.metadata.get("source") for c in chunks)),
                "chunks": [f"chunk_{i}" for i in range(len(chunks))]
            }
            
        except Exception as e:
            logger.error(f"Error during document ingestion: {e}", exc_info=True)
            return {
                "status": constants.ERROR,
                "message": f"Document ingestion failed: {str(e)}",
                "added_chunks": 0,
                "added_files": 0
            }
    
    def search(self, query: str, k: int = 5) -> List[Document]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents
        """
        try:
            results = self.db.similarity_search(query, k=k)
            logger.debug(f"Found {len(results)} results for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []
    
    def delete_all_documents(self) -> bool:
        """
        Delete all documents from the vector database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all documents and delete by IDs
            all_results = self.db.get()
            if all_results and all_results.get("ids"):
                self.db.delete(ids=all_results["ids"])
            logger.info("All documents deleted from vector database")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False


# Global instance
_vector_db_manager: Optional[VectorDatabaseManager] = None


def get_vector_db_manager() -> VectorDatabaseManager:
    """Get or create the global vector database manager instance."""
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorDatabaseManager()
    return _vector_db_manager


def ingest_to_vectordb(document_dir: str = constants.DOCUMENT_DATA_DIR) -> Dict[str, Any]:
    """
    Ingest documents to a vector database.
    
    Args:
        document_dir: Path to document directory
        
    Returns:
        Dictionary with ingestion results
    """
    manager = get_vector_db_manager()
    return manager.ingest_documents(document_dir)
