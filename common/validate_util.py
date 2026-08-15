from __future__ import annotations

import html
from typing import Any

import requests

from common import constants
from config.logger import Logger
from config.exceptions import ValidationError

logger = Logger.get_logger()

class ValidateUtil:
    """Common input validation helpers."""

    @staticmethod
    def _validate_with_llama_guard(normalized_prompt: str) -> None:
        """Run prompt safety moderation using the configured Llama Guard model."""
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
            raise ValidationError("Prompt blocked by Llama Guard safety policy.")

        if first_token != "safe":
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

