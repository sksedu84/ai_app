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
from config.exceptions import ValidationError

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
    def _validate_with_llama_guard(normalized_prompt: str) -> None:
        """Run prompt safety moderation using the configured Llama Guard model."""
        cached_token = ValidateUtil._get_unexpected_prompt(normalized_prompt)
        if cached_token is not None:
            logger.info("Prompt invalid from database: %s", cached_token)
            raise ValidationError("Prompt safety validation returned an unexpected result.")

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
            raise ValidationError("Unable to validate prompt safety with Llama Guard.") from exc

        model_response = str(payload.get("response", "")).strip().lower()
        first_token = model_response.split(maxsplit=1)[0] if model_response else ""
        logger.info("Llama Guard response: %s", first_token)
        if first_token == "unsafe":
            ValidateUtil._cache_unexpected_guard_token(normalized_prompt, first_token)
            raise ValidationError("Prompt blocked by Llama Guard safety policy.")

        if first_token != "safe":
            ValidateUtil._cache_unexpected_guard_token(normalized_prompt, first_token)
            raise ValidationError("Prompt safety validation returned an unexpected result.")

    @staticmethod
    def validate_prompt(prompt: str) -> str:
        # Validate RAG prompt text before processing.
        if prompt is None:
            raise ValidationError("Prompt is required.")

        if not isinstance(prompt, str):
            raise ValidationError("Prompt must be a string.")

        stripped_prompt = prompt.strip()
        if not stripped_prompt:
            raise ValidationError("Prompt must not be empty.")

        if stripped_prompt.startswith(constants.FORBIDDEN_WRAPPERS) or stripped_prompt.endswith(constants.FORBIDDEN_WRAPPERS):
            raise ValidationError("Prompt must not start or end with forbidden wrappers.")

        normalized_prompt = html.escape(stripped_prompt.replace("\n", " "))
        if len(normalized_prompt) > constants.MAX_PROMPT_LENGTH:
            raise ValidationError(f"Prompt exceeds the maximum length of {constants.MAX_PROMPT_LENGTH} characters.")

        ValidateUtil._validate_with_llama_guard(normalized_prompt)

        return normalized_prompt


def validate_prompt(prompt: str) -> str:
    """Backward-compatible helper for direct function imports."""
    return ValidateUtil.validate_prompt(prompt)

