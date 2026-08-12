from __future__ import annotations

import textwrap
from pathlib import Path

from config.settings import Settings


def _write_env_file(tmp_path: Path, content: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return env_file


def test_settings_parse_cors_wildcards_from_env(tmp_path: Path) -> None:
    env_file = _write_env_file(
        tmp_path,
        """
        CORS_ORIGINS=*
        CORS_ALLOW_METHODS=*
        CORS_ALLOW_HEADERS=*
        """,
    )

    parsed = Settings(_env_file=env_file)

    assert parsed.cors_origins == ["*"]
    assert parsed.cors_allow_methods == ["*"]
    assert parsed.cors_allow_headers == ["*"]



def test_settings_parse_comma_separated_cors_lists_from_env(tmp_path: Path) -> None:
    env_file = _write_env_file(
        tmp_path,
        """
        CORS_ORIGINS=http://localhost:3000, https://example.com
        CORS_ALLOW_METHODS=GET, POST
        CORS_ALLOW_HEADERS=Authorization, Content-Type
        """,
    )

    parsed = Settings(_env_file=env_file)

    assert parsed.cors_origins == ["http://localhost:3000", "https://example.com"]
    assert parsed.cors_allow_methods == ["GET", "POST"]
    assert parsed.cors_allow_headers == ["Authorization", "Content-Type"]



def test_settings_parse_json_cors_lists_from_env(tmp_path: Path) -> None:
    env_file = _write_env_file(
        tmp_path,
        """
        CORS_ORIGINS=["http://localhost:3000", "https://example.com"]
        CORS_ALLOW_METHODS=["GET", "POST"]
        CORS_ALLOW_HEADERS=["Authorization", "Content-Type"]
        """,
    )

    parsed = Settings(_env_file=env_file)

    assert parsed.cors_origins == ["http://localhost:3000", "https://example.com"]
    assert parsed.cors_allow_methods == ["GET", "POST"]
    assert parsed.cors_allow_headers == ["Authorization", "Content-Type"]

