"""Reranking utilities for scored retrieval results."""

import re
from time import perf_counter
from typing import Any, List, Optional, Tuple

from langchain_core.documents import Document

from common import constants
from config.logger import Logger

try:
    from sentence_transformers import CrossEncoder
except ImportError:  # pragma: no cover - optional runtime dependency
    CrossEncoder = None

logger = Logger.get_logger()


class RerankUtil:
    """Provides reranking methods for vector retrieval pipelines."""

    def __init__(self):
        pass

    _local_reranker: Optional[Any] = None
    _local_reranker_failed: bool = False

    @staticmethod
    def _tokenize_text(value: str) -> set[str]:
        """Split text into lowercase alphanumeric tokens for lexical scoring."""
        return set(re.findall(r"[a-z0-9]+", value.casefold()))

    def _get_local_reranker(self) -> Optional[Any]:
        """Lazily initialize a local cross-encoder reranker."""
        if self.__class__._local_reranker_failed:
            return None

        if self.__class__._local_reranker is not None:
            return self.__class__._local_reranker

        if CrossEncoder is None:
            self.__class__._local_reranker_failed = True
            logger.warning(
                "sentence-transformers is not installed; local reranker unavailable. "
                "Install dependencies and restart to enable model=%s",
                constants.LOCAL_RERANKER_MODEL,
            )
            return None

        try:
            start = perf_counter()
            model = CrossEncoder(
                constants.LOCAL_RERANKER_MODEL,
                max_length=constants.LOCAL_RERANKER_MAX_LENGTH,
            )
            self.__class__._local_reranker = model
            logger.info(
                "Initialized local reranker model=%s (duration_ms=%s)",
                constants.LOCAL_RERANKER_MODEL,
                round((perf_counter() - start) * 1000, 2),
            )
            return model
        except Exception as exc:
            self.__class__._local_reranker_failed = True
            logger.warning(
                "Failed to initialize local reranker model=%s; error=%s",
                constants.LOCAL_RERANKER_MODEL,
                exc,
            )
            return None

    def _local_cross_encoder_rerank(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int,
    ) -> List[Tuple[Document, float]]:
        """Use sentence-transformers cross-encoder as a local reranker."""
        model = self._get_local_reranker()
        if model is None:
            return []

        pairs = [
            (query, (doc.page_content or "")[:constants.LOCAL_RERANKER_DOC_MAX_CHARS])
            for doc, _ in documents
        ]
        if not pairs:
            return []

        start = perf_counter()
        scores = model.predict(
            pairs,
            batch_size=constants.LOCAL_RERANKER_BATCH_SIZE,
            show_progress_bar=False,
        )
        reranked_docs = [(documents[idx][0], float(scores[idx])) for idx in range(len(documents))]
        reranked_docs.sort(key=lambda item: item[1], reverse=True)
        logger.info(
            "Reranked %d documents using local model=%s (duration_ms=%s)",
            len(reranked_docs),
            constants.LOCAL_RERANKER_MODEL,
            round((perf_counter() - start) * 1000, 2),
        )
        return reranked_docs[:top_k]

    def _heuristic_rerank_documents(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int,
    ) -> List[Tuple[Document, float]]:
        """Fallback reranker using lexical overlap blended with vector similarity."""
        query_tokens = self._tokenize_text(query)
        if not query_tokens:
            return documents[:top_k]

        reranked: List[Tuple[Document, float]] = []
        for doc, vector_score in documents:
            doc_tokens = self._tokenize_text(doc.page_content or "")
            if not doc_tokens:
                overlap = 0.0
            else:
                overlap = len(query_tokens & doc_tokens) / len(query_tokens)

            combined_score = (0.7 * float(vector_score)) + (0.3 * overlap)
            reranked.append((doc, combined_score))

        reranked.sort(key=lambda item: item[1], reverse=True)
        return reranked[:top_k]

    def rerank_documents(
        self,
        query: str,
        documents: List[Tuple[Document, float]],
        top_k: int = 5,
    ) -> List[Tuple[Document, float]]:
        """Rerank documents with a local cross-encoder and fall back to heuristics."""
        if not documents or top_k <= 0:
            return []

        safe_top_k = min(top_k, len(documents))

        try:
            local_results = self._local_cross_encoder_rerank(query, documents, safe_top_k)
            if local_results:
                return local_results
        except Exception as exc:
            logger.warning("Error during local cross-encoder reranking; using heuristic fallback instead: %s", exc)

        return self._heuristic_rerank_documents(query, documents, safe_top_k)

