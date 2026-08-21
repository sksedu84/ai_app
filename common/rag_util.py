"""RAG (Retrieval-Augmented Generation) utilities for generating LLM responses from retrieved context."""

from time import perf_counter
from typing import Any, List, Tuple

import ollama
from langchain_core.documents import Document

from common import constants
from common.ai_app_util import AiAppUtil
from config.logger import Logger

logger = Logger.get_logger()

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Answer the user's question using only the information provided in the context below. "
    "If the context does not contain enough information to answer, say so clearly. "
    "Do not fabricate or guess information that is not in the context."
)

_PROMPT_TEMPLATE = """\
Context:
{context}

Question: {question}

Answer:"""


class RAGUtil:
    """Builds prompts and generates responses for the RAG pipeline using a local Ollama model."""

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def __init__(self):
        pass

    @staticmethod
    def build_context(documents: List[Any]) -> str:
        """Concatenate retrieved document chunks into a numbered context block.

        Args:
            documents: List of Documents or (Document, relevance_score) tuples.

        Returns:
            A multi-paragraph string suitable for insertion into a prompt.
        """
        parts: List[str] = []
        for idx, item in enumerate(documents, start=1):
            if isinstance(item, tuple) and len(item) == 2:
                doc, score = item
            else:
                doc, score = item, None

            source = (doc.metadata or {}).get("source", "unknown")
            content = (doc.page_content or "").strip()
            if not content:
                continue

            header = f"[{idx}] (source: {source}"
            if score is not None:
                header += f", relevance: {float(score):.3f}"
            header += ")"

            parts.append(f"{header}\n{content}")
        return "\n\n".join(parts)

    @staticmethod
    def format_prompt(context: str, question: str) -> str:
        """Inject *context* and *question* into the RAG prompt template.

        Args:
            context: Pre-built context string from :meth:`build_context`.
            question: The user's original question.

        Returns:
            Formatted prompt string ready to be sent to the model.
        """
        return _PROMPT_TEMPLATE.format(context=context, question=question)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    @staticmethod
    async def generate(
        question: str,
        documents: List[Any],
    ) -> str:
        """Generate a RAG answer from the local Ollama model.

        Builds a prompt from *documents*, calls :data:`~common.constants.RAG_MODEL`
        via the Ollama async client, and returns the sanitised HTML response.

        Args:
            question: The validated user prompt.
            documents: Reranked (Document, score) tuples to use as context.

        Returns:
            Safe HTML string containing the model's answer.

        Raises:
            Exception: Propagates any Ollama communication or model error.
        """
        context = RAGUtil.build_context(documents)
        user_prompt = RAGUtil.format_prompt(context, question)

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        logger.debug(
            "RAG prompt built for model=%s (context_chunks=%d, prompt_chars=%d)",
            constants.RAG_MODEL,
            len(documents),
            len(user_prompt),
        )

        start = perf_counter()
        try:
            client = ollama.AsyncClient(host=constants.OLLAMA_URL)
            response = await client.chat(
                model=constants.RAG_MODEL,
                messages=messages,
            )
            raw_answer: str = response.message.content or ""
        except Exception as exc:
            logger.error(
                "RAG generation failed for model=%s: %s",
                constants.RAG_MODEL,
                exc,
            )
            raise

        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "RAG generation complete model=%s (duration_ms=%s, response_chars=%d)",
            constants.RAG_MODEL,
            duration_ms,
            len(raw_answer),
        )

        return AiAppUtil.text_to_safe_html(raw_answer)

