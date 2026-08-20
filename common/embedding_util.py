"""Embedding utilities for Ollama-backed vector operations."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, List

import requests
from langchain_core.embeddings import Embeddings

from common import constants


class EmbeddingUtil(Embeddings):
    """Provides embedding APIs compatible with LangChain Embeddings."""

    def __init__(self):
        self.model = constants.EMBEDDING_MODEL
        self.base_url = constants.OLLAMA_URL.rstrip("/")
        self.batch_size = max(1, constants.EMBEDDING_API_BATCH_SIZE)
        self.max_workers = max(1, constants.EMBEDDING_FALLBACK_WORKERS)
        self.num_thread = constants.EMBEDDING_NUM_THREAD
        self.num_gpu = constants.EMBEDDING_NUM_GPU
        self.headers = {"Content-Type": constants.CONTENT_TYPE_JSON}
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

