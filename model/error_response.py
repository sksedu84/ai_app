from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Error response model."""
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred.",
                "request_id": "abc123def456"
            }
        }
    )

    error: str = Field(description="Error type or message")
    detail: str | None = Field(default=None, description="Detailed error message")
    request_id: str | None = Field(default=None, description="Request ID for tracking")
