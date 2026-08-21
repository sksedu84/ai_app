from __future__ import annotations

import hashlib
import html
from typing import Any, Optional

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from common import constants
from common.database import DatabaseConfig
from config.logger import Logger

logger = Logger.get_logger()

class ValidateUtil:
    """Common input validation helpers."""

    def __init__(self):
        pass

    _guard_cache_engine = None

    @staticmethod
    def _prompt_hash(normalized_prompt: str) -> str:
        return hashlib.sha256(normalized_prompt.encode(constants.ENCODING_UTF8)).hexdigest()

    @classmethod
    def _get_guard_cache_engine(cls):
        if cls._guard_cache_engine is None:
            cls._guard_cache_engine = create_engine(DatabaseConfig.psycopg2_db_con_as_string())
        return cls._guard_cache_engine

    @classmethod
    def _get_unexpected_prompt(cls, normalized_prompt: str) -> Optional[str]:

        prompt_hash = cls._prompt_hash(normalized_prompt)
        select_sql = text(
            """
            SELECT model_response
            FROM unexpected_prompt
            WHERE prompt_hash = :prompt_hash
            LIMIT 1
            """
        )
        try:
            with cls._get_guard_cache_engine().connect() as conn:
                cached = conn.execute(select_sql, {"prompt_hash": prompt_hash}).scalar_one_or_none()
            return str(cached) if cached is not None else None
        except SQLAlchemyError as exc:
            logger.warning("Unable to read prompt guard cache entry: %s", exc)
            return None

    @classmethod
    def _cache_unexpected_guard_token(cls, normalized_prompt: str, first_token: str) -> None:
        if not first_token:
            return

        upsert_sql = text(
            """
            INSERT INTO unexpected_prompt (prompt_hash, model_response)
            VALUES (:prompt_hash, :model_response)
            ON CONFLICT (prompt_hash)
            DO UPDATE SET
                model_response = EXCLUDED.model_response,
                last_seen_at = NOW(),
                hit_count = unexpected_prompt.hit_count + 1
            """
        )
        try:
            with cls._get_guard_cache_engine().begin() as conn:
                conn.execute(
                    upsert_sql,
                    {
                        "prompt_hash": cls._prompt_hash(normalized_prompt),
                        "model_response": first_token,
                    },
                )
        except SQLAlchemyError as exc:
            logger.warning("Unable to write prompt guard cache entry: %s", exc)

    @staticmethod
    def _validate_with_llama_guard(normalized_prompt: str) -> str:
        """Return prompt safety classification from Llama Guard as 'safe' or 'unsafe'."""

        guard_prompt = (
            "Classify the user input for safety. "
            "Reply with only one word: safe or unsafe.\n\n"
            f"User input:\n{normalized_prompt}"
        )

        try:
            response = requests.post(
                f"{constants.OLLAMA_URL.rstrip('/')}/api/generate",
                json={
                    "model": constants.GUARD_MODEL,
                    "prompt": guard_prompt,
                    "stream": False,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except requests.RequestException as exc:
            logger.warning("Unable to validate prompt safety with Llama Guard: %s", exc)
            return "unsafe"

        model_response = str(payload.get("response", "")).strip().lower()
        first_token = model_response.split(maxsplit=1)[0] if model_response else ""
        logger.info("Llama Guard response: %s", first_token)
        if first_token != "safe":
            ValidateUtil._cache_unexpected_guard_token(normalized_prompt, first_token)
            return "unsafe"
        else:
            return "safe"

    @staticmethod
    def validate_prompt(prompt: str) -> tuple[str, Optional[str]]:
        # Validate RAG prompt text before processing.
        if prompt is None:
            return "unsafe", None

        if not isinstance(prompt, str):
            return "unsafe", None

        stripped_prompt = prompt.strip()
        if not stripped_prompt:
            return "unsafe", None

        if stripped_prompt.startswith(constants.FORBIDDEN_WRAPPERS) or stripped_prompt.endswith(constants.FORBIDDEN_WRAPPERS):
            return "unsafe", None

        normalized_prompt = html.escape(stripped_prompt.replace("\n", " "))

        if len(normalized_prompt) > constants.MAX_PROMPT_LENGTH:
            return "unsafe", None

        safety_status = ValidateUtil._validate_with_llama_guard(normalized_prompt)
        if safety_status != "safe":
            return "unsafe", None

        return "safe", normalized_prompt


def validate_prompt(prompt: str) -> tuple[str, Optional[str]]:
    """Backward-compatible helper for direct function imports."""
    return ValidateUtil.validate_prompt(prompt)

