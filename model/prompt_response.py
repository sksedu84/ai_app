from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common import constants


class PromptResponse(BaseModel):
    """RAG prompt response model."""
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "ok",
                "response": "Response from LLM based on prompt: What is AI?"
            }
        }
    )

    status: str = Field(
        pattern=("^(%s|%s)$" % (constants.OK, constants.ERROR)),
        serialization_alias="status",
        description="Operation status"
    )
    response: str = Field(
        serialization_alias="response",
        description="LLM response to the prompt"
    )
