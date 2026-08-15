import json
from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from pydantic_settings import BaseSettings, DotEnvSettingsSource, EnvSettingsSource, PydanticBaseSettingsSource
from pydantic import Field, field_validator, ConfigDict


def _parse_cors_list_value(value: Any) -> list[str]:
    """Parse CORS settings from wildcard, comma-separated, JSON-array, or sequence input."""
    if value is None:
        return ["*"]

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized or normalized == "*":
            return ["*"]

        if normalized.startswith("["):
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                parsed = None
            else:
                if isinstance(parsed, list):
                    items = [str(item).strip() for item in parsed if str(item).strip()]
                    return items or ["*"]

        items = [item.strip() for item in normalized.split(",") if item.strip()]
        return items or ["*"]

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or ["*"]

    normalized = str(value).strip()
    return [normalized] if normalized else ["*"]


class _CorsParsingSettingsSourceMixin:
    """Normalize CORS env values before pydantic treats list fields as JSON-only complex types."""

    CORS_FIELDS: ClassVar[frozenset[str]] = frozenset({
        "cors_origins",
        "cors_allow_methods",
        "cors_allow_headers",
    })

    def prepare_field_value(self, field_name: str, field: Any, value: Any, value_is_complex: bool) -> Any:
        if field_name in self.CORS_FIELDS and value is not None:
            return _parse_cors_list_value(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class CorsEnvSettingsSource(_CorsParsingSettingsSourceMixin, EnvSettingsSource):
    """Environment settings source with tolerant CORS list parsing."""


class CorsDotEnvSettingsSource(_CorsParsingSettingsSourceMixin, DotEnvSettingsSource):
    """Dotenv settings source with tolerant CORS list parsing."""


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Supports .env file loading using pydantic-settings.
    """
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    app_name: str = Field(default="AI Assistant", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")

    # Server
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database
    db_host: Optional[str] = Field(default=None, alias="DB_HOST")
    db_port: Optional[int] = Field(default=None, alias="DB_PORT")
    db_user: Optional[str] = Field(default=None, alias="DB_USER")
    db_password: Optional[str] = Field(default=None, alias="DB_PASSWORD")
    db_name: Optional[str] = Field(default=None, alias="DB_NAME")

    # CORS
    cors_origins: list[str] = Field(
        default=["*"],
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed origins (or * for all)"
    )
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    # File Upload
    max_upload_size_mb: int = Field(default=100, alias="MAX_UPLOAD_SIZE_MB")
    upload_timeout_seconds: int = Field(default=300, alias="UPLOAD_TIMEOUT_SECONDS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s %(filename)s %(levelname)s %(message)s",
        alias="LOG_FORMAT"
    )

    # API Keys (for future LLM integration)
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        cors_env_settings = CorsEnvSettingsSource(
            settings_cls,
            case_sensitive=getattr(env_settings, "case_sensitive", None),
            env_prefix=getattr(env_settings, "env_prefix", None),
            env_prefix_target=getattr(env_settings, "env_prefix_target", None),
            env_nested_delimiter=getattr(env_settings, "env_nested_delimiter", None),
            env_nested_max_split=getattr(env_settings, "env_nested_max_split", None),
            env_ignore_empty=getattr(env_settings, "env_ignore_empty", None),
            env_parse_none_str=getattr(env_settings, "env_parse_none_str", None),
            env_parse_enums=getattr(env_settings, "env_parse_enums", None),
        )
        cors_dotenv_settings = CorsDotEnvSettingsSource(
            settings_cls,
            env_file=getattr(dotenv_settings, "env_file", None),
            env_file_encoding=getattr(dotenv_settings, "env_file_encoding", None),
            case_sensitive=getattr(dotenv_settings, "case_sensitive", None),
            env_prefix=getattr(dotenv_settings, "env_prefix", None),
            env_prefix_target=getattr(dotenv_settings, "env_prefix_target", None),
            env_nested_delimiter=getattr(dotenv_settings, "env_nested_delimiter", None),
            env_nested_max_split=getattr(dotenv_settings, "env_nested_max_split", None),
            env_ignore_empty=getattr(dotenv_settings, "env_ignore_empty", None),
            env_parse_none_str=getattr(dotenv_settings, "env_parse_none_str", None),
            env_parse_enums=getattr(dotenv_settings, "env_parse_enums", None),
        )
        return init_settings, cors_env_settings, cors_dotenv_settings, file_secret_settings

    @field_validator('cors_origins', 'cors_allow_methods', 'cors_allow_headers', mode='before')
    @classmethod
    def parse_cors_list(cls, value: Any) -> list[str]:
        """Parse CORS settings from wildcard, comma-separated, JSON-array, or sequence input."""
        return _parse_cors_list_value(value)



# Global settings instance
settings = Settings()
