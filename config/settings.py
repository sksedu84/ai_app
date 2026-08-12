import json
from collections.abc import Sequence
from typing import Annotated, Any, Optional

from pydantic_settings import BaseSettings, NoDecode
from pydantic import Field, field_validator, ConfigDict


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
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["*"],
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed origins (or * for all)"
    )
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

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

    @field_validator('cors_origins', 'cors_allow_methods', 'cors_allow_headers', mode='before')
    @classmethod
    def parse_cors_list(cls, value: Any) -> list[str]:
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



# Global settings instance
settings = Settings()
