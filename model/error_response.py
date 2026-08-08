from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str | None = None
    request_id: str | None = None
