"""
Vector database and embedding utilities for the RAG pipeline.

This module handles document ingestion, chunking, embedding, and vector storage.
Uses PostgreSQL with pgvector for production-grade vector storage.
"""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, text

from common import constants
from config.logger import Logger
from common.database import DatabaseConfig

logger = Logger.get_logger()


class FastOllamaEmbeddings(Embeddings):
    """Embedding wrapper that prefers Ollama's batch `/api/embed` endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str,
        batch_size: int = constants.EMBEDDING_API_BATCH_SIZE,
        max_workers: int = constants.EMBEDDING_FALLBACK_WORKERS,
        num_thread: Optional[int] = constants.EMBEDDING_NUM_THREAD,
        num_gpu: Optional[int] = constants.EMBEDDING_NUM_GPU,
        headers: Optional[dict] = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.batch_size = max(1, batch_size)
        self.max_workers = max(1, max_workers)
        self.num_thread = num_thread
        self.num_gpu = num_gpu
        self.headers = {
            "Content-Type": "application/json",
            **(headers or {}),
        }
        self.session = requests.Session()

    def _request_payload(self, *, key: str, value: Any) -> dict:
        payload = {
            "model": self.model,
            key: value,
        }
        options = {}
        if self.num_thread is not None:
            options["num_thread"] = self.num_thread
        if self.num_gpu is not None:
            options["num_gpu"] = self.num_gpu
        if options:
            payload["options"] = options
        return payload

    def _embed_single_legacy(self, text: str) -> List[float]:
        response = self.session.post(
            f"{self.base_url}/api/embeddings",
            headers=self.headers,
            json=self._request_payload(key="prompt", value=text),
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding")
        if not embedding:
            raise ValueError("Missing 'embedding' in Ollama /api/embeddings response")
        return embedding

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.session.post(
            f"{self.base_url}/api/embed",
            headers=self.headers,
            json=self._request_payload(key="input", value=texts),
            timeout=180,
        )
        if response.status_code == 404:
            # Older Ollama releases may not expose /api/embed.
            raise RuntimeError("Ollama /api/embed not available")

        response.raise_for_status()
        payload = response.json()

        embeddings = payload.get("embeddings")
        if embeddings:
            return embeddings

        single_embedding = payload.get("embedding")
        if single_embedding:
            return [single_embedding]

        raise ValueError("Missing embedding payload in Ollama /api/embed response")

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            all_embeddings.extend(self._embed_batch(batch))
        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        instruction_pairs = [f"passage: {text}" for text in texts]
        try:
            return self._embed_documents(instruction_pairs)
        except Exception:
            # Fallback path for older servers: parallelize single-text requests.
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                return list(executor.map(self._embed_single_legacy, instruction_pairs))

    def embed_query(self, text: str) -> List[float]:
        instruction_pair = f"query: {text}"
        try:
            return self._embed_batch([instruction_pair])[0]
        except Exception:
            return self._embed_single_legacy(instruction_pair)


class VectorDatabaseManager:
    """Manages vector database operations for document embeddings using PostgreSQL with pgvector."""

    # Collection/table name
    COLLECTION_NAME: str = "documents"
    
    def __init__(self):
        """Initialize the vector database manager with PostgreSQL pgvector."""
        self.embeddings = FastOllamaEmbeddings(
            model=constants.EMBEDDING_MODEL,
            base_url=constants.OLLAMA_URL,
            batch_size=constants.EMBEDDING_API_BATCH_SIZE,
            max_workers=constants.EMBEDDING_FALLBACK_WORKERS,
        )
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize the vector database connection with pgvector."""
        try:
            connection_string = DatabaseConfig.psycopg_db_con_as_string()

            # Test connection
            self.engine = create_engine(connection_string)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Initialize PGVector store
            self.db = PGVector(
                embeddings=self.embeddings,
                collection_name=self.COLLECTION_NAME,
                connection=connection_string,
                use_jsonb=True,
            )

            logger.info("PostgreSQL pgvector database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            raise

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        """Return elapsed milliseconds from a perf_counter start value."""
        return round((perf_counter() - start) * 1000, 2)

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
            text_docs = txt_loader.load()
            docs.extend(text_docs)
            logger.info(f"Loaded {len(text_docs)} text documents")
        except Exception as e:
            logger.error(f"Error loading text documents: {e}")
        
        try:
            # Load PDF files
            pdf_loader = DirectoryLoader(
                str(doc_path),
                glob="**/*.pdf",
                loader_cls=PyPDFLoader
            )
            pdf_docs = pdf_loader.load()
            docs.extend(pdf_docs)
            logger.info(f"Loaded {len(pdf_docs)} PDF documents")
        except Exception as e:
            logger.error(f"Error loading PDF documents: {e}")
        
        try:
            # Load DOCX files
            docx_loader = DirectoryLoader(
                str(doc_path),
                glob="**/*.docx",
                loader_cls=Docx2txtLoader
            )
            docx_docs = docx_loader.load()
            docs.extend(docx_docs)
            logger.info(f"Loaded {len(docx_docs)} DOCX documents")
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
            stored_hash = self._get_stored_file_hash(str(file_path))
            return stored_hash != file_hash
        except Exception as e:
            logger.warning(f"Could not check if document needs reindexing: {e}")
            return True

    def _get_stored_file_hash(self, source_file: str) -> Optional[str]:
        """Fetch the stored hash for a file from the vector metadata table."""
        sql = text(
            """
            SELECT e.cmetadata->>:file_hash_key AS file_hash
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON c.uuid = e.collection_id
            WHERE c.name = :collection_name
              AND e.cmetadata->>:source_key = :source_file
            LIMIT 1
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "file_hash_key": constants.FILE_HASH,
                    "source_key": constants.SOURCE_FILE,
                    "collection_name": self.COLLECTION_NAME,
                    "source_file": source_file,
                },
            ).scalar_one_or_none()
            return str(result) if result else None
        return None

    def _get_source_chunk_ids(self, source_file: str) -> List[str]:
        """Collect vector row IDs for a source file so they can be replaced."""
        sql = text(
            """
            SELECT e.id
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON c.uuid = e.collection_id
            WHERE c.name = :collection_name
              AND e.cmetadata->>:source_key = :source_file
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(
                sql,
                {
                    "collection_name": self.COLLECTION_NAME,
                    "source_key": constants.SOURCE_FILE,
                    "source_file": source_file,
                },
            ).all()
            return [str(row[0]) for row in rows if row and row[0] is not None]
        return None

    def ingest_documents(self, document_dir: str = constants.DOCUMENT_DATA_DIR) -> Dict[str, Any]:
        """
        Ingest documents from a directory into a vector database.
        
        Args:
            document_dir: Path to document directory
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting document ingestion from {document_dir}")
        total_start = perf_counter()
        stage_timings_ms: Dict[str, float] = {}

        try:
            # Load documents
            load_start = perf_counter()
            documents = self._load_documents(document_dir)
            stage_timings_ms["load_documents"] = self._elapsed_ms(load_start)
            if not documents:
                logger.warning("No documents found to ingest")
                return {
                    "status": constants.OK,
                    "message": "No documents found",
                    "added_chunks": 0,
                    "added_files": 0,
                    "timings_ms": {
                        **stage_timings_ms,
                        "total": self._elapsed_ms(total_start),
                    },
                }
            
            # Keep unchanged files out of chunking/embedding work.
            reindex_start = perf_counter()
            file_hash_cache: Dict[str, str] = {}
            source_needs_reindex: Dict[str, bool] = {}
            filtered_documents: List[Document] = []

            for document in documents:
                source = document.metadata.get("source")
                if not source:
                    filtered_documents.append(document)
                    continue

                source_key = str(Path(source))
                if source_key not in source_needs_reindex:
                    current_hash = self._get_file_hash(Path(source_key))
                    file_hash_cache[source_key] = current_hash
                    source_needs_reindex[source_key] = (
                        self._get_stored_file_hash(source_key) != current_hash
                    )

                if source_needs_reindex[source_key]:
                    filtered_documents.append(document)
            stage_timings_ms["check_reindex"] = self._elapsed_ms(reindex_start)

            if not filtered_documents:
                skipped_files = len(source_needs_reindex)
                logger.info("No changed documents detected; skipping re-ingestion")
                return {
                    "status": constants.OK,
                    "message": "No changed documents found",
                    "added_chunks": 0,
                    "added_files": 0,
                    "skipped_files": skipped_files,
                    "timings_ms": {
                        **stage_timings_ms,
                        "total": self._elapsed_ms(total_start),
                    },
                }

            # Remove old vectors for changed sources before adding replacement chunks.
            delete_start = perf_counter()
            for source_key, should_reindex in source_needs_reindex.items():
                if not should_reindex:
                    continue
                existing_ids = self._get_source_chunk_ids(source_key)
                if existing_ids:
                    self.db.delete(ids=existing_ids)
            stage_timings_ms["delete_old_vectors"] = self._elapsed_ms(delete_start)

            # Chunk documents
            chunk_start = perf_counter()
            chunks = self._chunk_documents(filtered_documents)
            stage_timings_ms["chunk_documents"] = self._elapsed_ms(chunk_start)

            # Add metadata to chunks. Cache file hashes by source to avoid
            # recalculating the same hash for every chunk from one document.
            metadata_start = perf_counter()
            for chunk in chunks:
                source = chunk.metadata.get("source")
                if not source:
                    continue

                source_path = Path(source)
                source_key = str(source_path)
                if source_key not in file_hash_cache:
                    file_hash_cache[source_key] = self._get_file_hash(source_path)

                chunk.metadata[constants.FILE_HASH] = file_hash_cache[source_key]
                chunk.metadata[constants.SOURCE_FILE] = source_key
            stage_timings_ms["prepare_metadata"] = self._elapsed_ms(metadata_start)

            # Add chunks to vector database
            try:
                insert_start = perf_counter()
                total_batches = (len(chunks) + constants.VECTOR_DB_BATCH_SIZE - 1) // constants.VECTOR_DB_BATCH_SIZE
                for i in range(0, len(chunks), constants.VECTOR_DB_BATCH_SIZE):
                    chunk_batch = chunks[i:i + constants.VECTOR_DB_BATCH_SIZE]
                    self.db.add_documents(chunk_batch)
                    current_batch = (i // constants.VECTOR_DB_BATCH_SIZE) + 1
                    if current_batch % 10 == 0 or current_batch == total_batches:
                        logger.info(
                            "Embedding insert progress: batch %d/%d, chunks_processed=%d",
                            current_batch,
                            total_batches,
                            min(i + len(chunk_batch), len(chunks)),
                        )
                stage_timings_ms["insert_vectors"] = self._elapsed_ms(insert_start)
                logger.info(f"Successfully ingested {len(chunks)} chunks from {len(filtered_documents)} documents")
            except Exception as add_error:
                logger.error(f"Error adding documents to PGVector: {add_error}")
                raise

            stage_timings_ms["total"] = self._elapsed_ms(total_start)
            logger.info(
                "Ingestion timings ms: total=%s load=%s reindex=%s delete=%s chunk=%s metadata=%s insert=%s",
                stage_timings_ms.get("total", 0.0),
                stage_timings_ms.get("load_documents", 0.0),
                stage_timings_ms.get("check_reindex", 0.0),
                stage_timings_ms.get("delete_old_vectors", 0.0),
                stage_timings_ms.get("chunk_documents", 0.0),
                stage_timings_ms.get("prepare_metadata", 0.0),
                stage_timings_ms.get("insert_vectors", 0.0),
            )

            return {
                "status": constants.OK,
                "message": "Documents ingested successfully",
                "added_chunks": len(chunks),
                "added_files": len(set(c.metadata.get("source") for c in chunks if c.metadata.get("source"))),
                "skipped_files": sum(1 for reindex in source_needs_reindex.values() if not reindex),
                "chunks": [f"chunk_{i}" for i in range(len(chunks))],
                "timings_ms": stage_timings_ms,
            }
            
        except Exception as e:
            logger.error(f"Error during document ingestion: {e}", exc_info=True)
            return {
                "status": constants.ERROR,
                "message": f"Document ingestion failed: {str(e)}",
                "added_chunks": 0,
                "added_files": 0,
                "timings_ms": {
                    **stage_timings_ms,
                    "total": self._elapsed_ms(total_start),
                },
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
            # Preferred API for langchain_postgres.
            if hasattr(self.db, "delete_collection"):
                self.db.delete_collection()
                if hasattr(self.db, "create_collection"):
                    self.db.create_collection()
            else:
                # Backward-compatible path for legacy stores.
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
