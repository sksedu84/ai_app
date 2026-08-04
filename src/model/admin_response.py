from pydantic import BaseModel, ConfigDict, Field

from src.common import constants


class AdminResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    ai_response: str = Field(serialization_alias="aiResponse")
    status: str = Field(pattern=("^(%s|%s)$" % (constants.OK, constants.ERROR)), serialization_alias="status")
    uploaded_files: list[str] = Field(default_factory=list, serialization_alias="uploadedFiles")
    added_files: int = Field(default=0, serialization_alias="addedFiles")
    updated_files: int = Field(default=0, serialization_alias="updatedFiles")
    deleted_files: int = Field(default=0, serialization_alias="deletedFiles")
    skipped_files: int = Field(default=0, serialization_alias="skippedFiles")
    added_chunks: int = Field(default=0, serialization_alias="addedChunks")
