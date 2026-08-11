from pydantic import BaseModel, ConfigDict, Field

from common import constants


class PromptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern=("^(%s|%s)$" % (constants.OK, constants.ERROR)), serialization_alias="status")
    response: str = Field(serialization_alias="response")
