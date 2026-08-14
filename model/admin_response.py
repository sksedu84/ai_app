from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common import constants


STATUS_PATTERN = rf"^({constants.OK}|{constants.ERROR})$"
ADMIN_RESPONSE_EXAMPLE = {
    "aiResponse": "Welcome to admin page.",
    "status": "ok",
    "uploadedFiles": ["documents/example.txt"],
    "addedFiles": 0,
    "addedChunks": 0,
}


class AdminResponse(BaseModel):
    """Admin endpoint response model."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"example": ADMIN_RESPONSE_EXAMPLE},
    )

    ai_response: str = Field(
        serialization_alias="aiResponse",
        description="Response message from admin service"
    )
    status: str = Field(
        pattern=STATUS_PATTERN,
        serialization_alias="status",
        description="Operation status",
    )
    uploaded_files: list[str] = Field(
        default_factory=list,
        serialization_alias="uploadedFiles",
        description="List of uploaded files"
    )
    added_files: int = Field(
        default=0,
        serialization_alias="addedFiles",
        ge=0,
        description="Number of files added"
    )
    added_chunks: int = Field(
        default=0,
        serialization_alias="addedChunks",
        ge=0,
        description="Number of chunks added"
    )
