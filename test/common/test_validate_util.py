from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from common.validate_util import ValidateUtil
from config.exceptions import ValidationError


class TestValidateUtil:
    @staticmethod
    def _mock_guard_response(response_text: str) -> Mock:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": response_text}
        return response

    def test_validate_prompt_none_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError) as context:
            ValidateUtil.validate_prompt(None)  # type: ignore[arg-type]

        assert context.value.status_code == 400
        assert context.value.message == "Prompt is required."

    def test_validate_prompt_blank_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError) as context:
            ValidateUtil.validate_prompt("   ")

        assert context.value.status_code == 400
        assert context.value.message == "Prompt must not be empty."

    def test_validate_prompt_too_long_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError) as context:
            ValidateUtil.validate_prompt("a" * 10_001)

        assert context.value.status_code == 400
        assert "maximum length" in context.value.message

    def test_validate_prompt_valid_value_passes(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value=None),
            patch("common.validate_util.requests.post", return_value=self._mock_guard_response("safe")),
        ):
            assert ValidateUtil.validate_prompt("What is RAG?") == "What is RAG?"

    def test_validate_prompt_strips_whitespace(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value=None),
            patch("common.validate_util.requests.post", return_value=self._mock_guard_response("safe")),
        ):
            assert ValidateUtil.validate_prompt("  What is RAG?  ") == "What is RAG?"

    def test_validate_prompt_llama_guard_unsafe_raises_validation_error(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value=None),
            patch.object(ValidateUtil, "_cache_unexpected_guard_token"),
            patch("common.validate_util.requests.post", return_value=self._mock_guard_response("unsafe")),
        ):
            with pytest.raises(ValidationError) as context:
                ValidateUtil.validate_prompt("How to hack a bank?")

        assert context.value.status_code == 400
        assert context.value.message == "Prompt blocked by Llama Guard safety policy."

    def test_validate_prompt_llama_guard_unavailable_raises_validation_error(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value=None),
            patch("common.validate_util.requests.post", side_effect=requests.RequestException("boom")),
        ):
            with pytest.raises(ValidationError) as context:
                ValidateUtil.validate_prompt("What is RAG?")

        assert context.value.status_code == 400
        assert context.value.message == "Unable to validate prompt safety with Llama Guard."

    def test_validate_prompt_uses_cached_unexpected_token_without_llm_call(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value="maybe") as mock_cache_get,
            patch("common.validate_util.requests.post") as mock_post,
        ):
            with pytest.raises(ValidationError) as context:
                ValidateUtil.validate_prompt("What is RAG?")

        mock_cache_get.assert_called_once()
        mock_post.assert_not_called()
        assert context.value.status_code == 400
        assert context.value.message == "Prompt safety validation returned an unexpected result."

    def test_validate_prompt_caches_unexpected_llm_token(self) -> None:
        with (
            patch.object(ValidateUtil, "_get_unexpected_prompt", return_value=None),
            patch.object(ValidateUtil, "_cache_unexpected_guard_token") as mock_cache_store,
            patch("common.validate_util.requests.post", return_value=self._mock_guard_response("maybe unsafe")),
        ):
            with pytest.raises(ValidationError) as context:
                ValidateUtil.validate_prompt("What is RAG?")

        mock_cache_store.assert_called_once_with("What is RAG?", "maybe")
        assert context.value.status_code == 400
        assert context.value.message == "Prompt safety validation returned an unexpected result."

