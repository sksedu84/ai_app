"""
Vector database and embedding utilities for the RAG pipeline.

This module handles document ingestion, chunking, embedding, and vector storage.
Uses PostgreSQL with pgvector for production-grade vector storage.
"""

import hashlib
import re
from collections import Counter, defaultdict
from time import perf_counter
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_postgres import PGVector
from langchain_core.documents import Document
from sqlalchemy import create_engine, text

from common import constants
from common.embedding_util import EmbeddingUtil
from config.logger import Logger
from common.database import DatabaseConfig

logger = Logger.get_logger()


class VectorDatabaseManager(EmbeddingUtil):
    """Manages vector database operations for document embeddings using PostgreSQL with pgvector."""

    # Collection/table name
    COLLECTION_NAME: str = "documents"

    def __init__(self):
        """Initialize embedding and vector database management with pgvector."""
        super().__init__()
        self._initialize_db()


    def _initialize_db(self) -> None:
        """Initialize the vector database connection with pgvector."""
        try:
            self.engine = create_engine(DatabaseConfig.psycopg_db_con_as_string())

            # Initialize PGVector store
            self.db = PGVector(
                embeddings=self,
                collection_name=self.COLLECTION_NAME,
                connection=DatabaseConfig.psycopg_db_con_as_string(),
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

    @staticmethod
    def _extract_edge_line(lines: List[str], from_start: bool = True) -> str:
        """Return the first/last non-empty line from a page's lines."""
        iterable = lines if from_start else reversed(lines)
        for line in iterable:
            cleaned = line.strip()
            if cleaned:
                return cleaned
        return ""

    @staticmethod
    def _line_signature(line: str) -> str:
        """Normalize edge lines so variable page numbers still match."""
        lowered = line.casefold().strip()
        lowered = re.sub(r"\d+", "#", lowered)
        return re.sub(r"\s+", " ", lowered)

    @classmethod
    def _strip_headers_and_footers(cls, documents: List[Document]) -> Tuple[List[Document], int]:
        """Remove repeated page-level headers/footers before chunking and embedding."""
        if not documents:
            return documents, 0

        docs_by_source: Dict[str, List[int]] = defaultdict(list)
        for idx, doc in enumerate(documents):
            source = str(Path(doc.metadata.get("source", ""))) if doc.metadata else ""
            if source:
                docs_by_source[source].append(idx)

        if not docs_by_source:
            return documents, 0

        updated = list(documents)
        cleaned_pages = 0

        for _, indexes in docs_by_source.items():
            if len(indexes) < 2:
                continue

            header_signatures: List[str] = []
            footer_signatures: List[str] = []
            edge_cache: Dict[int, Tuple[str, str]] = {}

            for index in indexes:
                lines = updated[index].page_content.splitlines()
                top_line = cls._extract_edge_line(lines, from_start=True)
                bottom_line = cls._extract_edge_line(lines, from_start=False)
                edge_cache[index] = (top_line, bottom_line)
                if top_line:
                    header_signatures.append(cls._line_signature(top_line))
                if bottom_line:
                    footer_signatures.append(cls._line_signature(bottom_line))

            threshold = max(2, int(len(indexes) * 0.6))
            repeated_headers = {
                signature
                for signature, count in Counter(header_signatures).items()
                if count >= threshold
            }
            repeated_footers = {
                signature
                for signature, count in Counter(footer_signatures).items()
                if count >= threshold
            }

            if not repeated_headers and not repeated_footers:
                continue

            for index in indexes:
                doc = updated[index]
                lines = doc.page_content.splitlines()
                if not lines:
                    continue

                top_line, bottom_line = edge_cache[index]
                start = 0
                end = len(lines)

                if top_line and cls._line_signature(top_line) in repeated_headers:
                    while start < end and not lines[start].strip():
                        start += 1
                    if start < end and lines[start].strip() == top_line:
                        start += 1

                if bottom_line and cls._line_signature(bottom_line) in repeated_footers:
                    while end > start and not lines[end - 1].strip():
                        end -= 1
                    if end > start and lines[end - 1].strip() == bottom_line:
                        end -= 1

                if start == 0 and end == len(lines):
                    continue

                cleaned_content = "\n".join(lines[start:end]).strip()
                if cleaned_content and cleaned_content != doc.page_content:
                    doc.page_content = cleaned_content
                    cleaned_pages += 1

        return updated, cleaned_pages

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

    def _get_existing_source_for_hash(self, file_hash: str) -> Optional[str]:
        """Find any existing source path that already has the same file hash."""
        sql = text(
            """
            SELECT e.cmetadata->>:source_key AS source_file
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON c.uuid = e.collection_id
            WHERE c.name = :collection_name
              AND e.cmetadata->>:file_hash_key = :file_hash
            LIMIT 1
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "collection_name": self.COLLECTION_NAME,
                    "source_key": constants.SOURCE_FILE,
                    "file_hash_key": constants.FILE_HASH,
                    "file_hash": file_hash,
                },
            ).scalar_one_or_none()
            return str(result) if result else None

    def _update_source_metadata(self, current_source: str, new_source: str, file_hash: str) -> int:
        """Update stored source metadata for a renamed file without re-embedding."""
        sql = text(
            f"""
            UPDATE langchain_pg_embedding AS e
            SET cmetadata = jsonb_set(
                jsonb_set(e.cmetadata, '{{{constants.SOURCE_FILE}}}', to_jsonb(CAST(:new_source AS text)), true),
                '{{source}}',
                to_jsonb(CAST(:new_source AS text)),
                true
            )
            FROM langchain_pg_collection AS c
            WHERE c.uuid = e.collection_id
              AND c.name = :collection_name
              AND e.cmetadata->>'{constants.SOURCE_FILE}' = :current_source
              AND e.cmetadata->>'{constants.FILE_HASH}' = :file_hash
            """
        )
        with self.engine.begin() as conn:
            result = conn.execute(
                sql,
                {
                    "collection_name": self.COLLECTION_NAME,
                    "current_source": current_source,
                    "new_source": new_source,
                    "file_hash": file_hash,
                },
            )
            return result.rowcount or 0

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

            clean_start = perf_counter()
            documents, cleaned_pages = self._strip_headers_and_footers(documents)
            stage_timings_ms["clean_headers_footers"] = self._elapsed_ms(clean_start)
            if cleaned_pages:
                logger.info("Removed repeated headers/footers from %d pages", cleaned_pages)

            # Keep unchanged files out of chunking/embedding work.
            reindex_start = perf_counter()
            current_sources = {
                str(Path(source))
                for source in (document.metadata.get("source") for document in documents)
                if source
            }
            file_hash_cache: Dict[str, str] = {}
            source_needs_reindex: Dict[str, bool] = {}
            renamed_files = 0
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

                    stored_hash = self._get_stored_file_hash(source_key)
                    if stored_hash is not None:
                        source_needs_reindex[source_key] = stored_hash != current_hash
                    else:
                        existing_source = self._get_existing_source_for_hash(current_hash)
                        is_renamed_file = (
                            existing_source
                            and existing_source != source_key
                            and existing_source not in current_sources
                        )
                        if is_renamed_file:
                            updated_rows = self._update_source_metadata(
                                current_source=existing_source,
                                new_source=source_key,
                                file_hash=current_hash,
                            )
                            if updated_rows > 0:
                                renamed_files += 1
                                logger.info(
                                    "Updated metadata for renamed file '%s' (previous source '%s', updated chunks=%d)",
                                    source_key,
                                    existing_source,
                                    updated_rows,
                                )
                                source_needs_reindex[source_key] = False
                            else:
                                logger.warning(
                                    "Rename detected from '%s' to '%s' but no stored metadata rows were updated; re-indexing instead",
                                    existing_source,
                                    source_key,
                                )
                                source_needs_reindex[source_key] = True
                        else:
                            source_needs_reindex[source_key] = True

                if source_needs_reindex[source_key]:
                    filtered_documents.append(document)
            stage_timings_ms["check_reindex"] = self._elapsed_ms(reindex_start)

            if not filtered_documents:
                skipped_files = len(source_needs_reindex)
                message = "No changed documents found"
                if renamed_files:
                    message = "Renamed files detected; updated stored metadata without re-embedding"
                    logger.info("No content changes detected; updated rename metadata and skipped re-ingestion")
                else:
                    logger.info("No changed documents detected; skipping re-ingestion")
                return {
                    "status": constants.OK,
                    "message": message,
                    "added_chunks": 0,
                    "added_files": 0,
                    "skipped_files": skipped_files,
                    "renamed_files": renamed_files,
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
                "renamed_files": renamed_files,
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

    @staticmethod
    def _dedupe_documents(documents: List[Document]) -> List[Document]:
        """Drop duplicate chunks that may appear in fallback search paths."""
        seen = set()
        unique_documents: List[Document] = []
        for doc in documents:
            source = doc.metadata.get("source") if doc.metadata else ""
            key = (source, doc.page_content)
            if key in seen:
                continue
            seen.add(key)
            unique_documents.append(doc)
        return unique_documents

    @staticmethod
    def _dedupe_scored_documents(documents: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """Drop duplicate chunks while keeping the highest score for each unique chunk."""
        best_by_key: Dict[Tuple[str, str], Tuple[Document, float]] = {}
        for doc, score in documents:
            source = doc.metadata.get("source") if doc.metadata else ""
            key = (source, doc.page_content)
            current = best_by_key.get(key)
            if current is None or score > current[1]:
                best_by_key[key] = (doc, score)
        return list(best_by_key.values())

    @staticmethod
    def _normalize_text(value: str) -> str:
        """Normalize text for a stable literal containment check."""
        return " ".join(value.casefold().split())

    def _boost_exact_matches(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """Raise exact literal matches to a perfect relevance score.

        The vector store score is semantic similarity, so an exact phrase can still
        produce a mid-range score. When the query text is literally present inside
        a chunk, treat that as a perfect match and keep the semantic score only for
        non-exact results.
        """
        normalized_query = self._normalize_text(query)
        if not normalized_query:
            return documents

        boosted_results: List[Tuple[Document, float]] = []
        for doc, score in documents:
            content = self._normalize_text(doc.page_content or "")
            if normalized_query in content:
                boosted_results.append((doc, 1.0))
            else:
                boosted_results.append((doc, score))
        return boosted_results

    def search(self, query: str, k: int = 10) -> List[Document]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents
        """
        try:
            safe_k = max(1, min(k, constants.VECTOR_SEARCH_MAX_K))
            start = perf_counter()
            strategy = "similarity"
            results: List[Document] = []

            if hasattr(self.db, "max_marginal_relevance_search"):
                strategy = "mmr"
                results = self.db.max_marginal_relevance_search(
                    query,
                    k=safe_k,
                    fetch_k=max(constants.VECTOR_SEARCH_FETCH_K, safe_k),
                    lambda_mult=constants.VECTOR_SEARCH_MMR_LAMBDA,
                )

            # If MMR is unavailable or returns no hits, use scored similarity and
            # drop weak matches before falling back to plain similarity.
            if not results and hasattr(self.db, "similarity_search_with_relevance_scores"):
                strategy = "scored_similarity"
                scored_results = self.db.similarity_search_with_relevance_scores(
                    query,
                    k=max(constants.VECTOR_SEARCH_FETCH_K, safe_k),
                )
                filtered_docs = [
                    doc
                    for doc, score in scored_results
                    if score >= constants.VECTOR_SEARCH_MIN_RELEVANCE
                ]
                results = filtered_docs[:safe_k]

            if not results:
                strategy = "similarity"
                results = self.db.similarity_search(query, k=safe_k)

            results = self._dedupe_documents(results)
            duration_ms = self._elapsed_ms(start)
            logger.debug(
                "Found %d results using strategy=%s (k=%d, duration_ms=%s)",
                len(results),
                strategy,
                safe_k,
                duration_ms,
            )
            return results
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []

    def similarity_search(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """
        Search for documents similar to the query and return relevance scores.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        try:
            safe_k = max(1, min(k, constants.VECTOR_SEARCH_MAX_K))
            start = perf_counter()
            strategy = "scored_similarity"

            if hasattr(self.db, "similarity_search_with_relevance_scores"):
                raw_results = self.db.similarity_search_with_relevance_scores(
                    query,
                    k=max(constants.VECTOR_SEARCH_FETCH_K, safe_k),
                )
                scored_results = self._boost_exact_matches(
                    query,
                    [(doc, float(score)) for doc, score in raw_results],
                )
                scored_results = [
                    (doc, score)
                    for doc, score in scored_results
                    if score >= constants.VECTOR_SEARCH_MIN_RELEVANCE
                ]
            else:
                strategy = "similarity_fallback"
                docs = self.db.similarity_search(query, k=safe_k)
                # Score is unavailable on this path; use a neutral placeholder.
                scored_results = [(doc, 0.0) for doc in docs]

            scored_results = self._dedupe_scored_documents(scored_results)
            scored_results.sort(key=lambda item: item[1], reverse=True)
            scored_results = scored_results[:safe_k]

            duration_ms = self._elapsed_ms(start)
            logger.debug(
                "Found %d scored results using strategy=%s (k=%d, duration_ms=%s)",
                len(scored_results),
                strategy,
                safe_k,
                duration_ms,
            )
            return scored_results
        except Exception as e:
            logger.error(f"Error during scored similarity search: {e}")
            return []

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
