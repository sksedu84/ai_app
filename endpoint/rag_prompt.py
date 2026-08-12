import time
from fastapi import APIRouter, HTTPException, Query

from common import constants
from config.logger import Logger
from model.prompt_response import PromptResponse

logger = Logger.get_logger()


class RAGPromptEndpoint:
    def __init__(self):
        self.router = APIRouter(tags=["RAG"])

        self.router.add_api_route(
            "/rag",
            self.rag_prompt,
            methods=["GET"],
            response_model=PromptResponse,
        )

    @staticmethod
    async def rag_prompt(
        prompt: str = Query(default=None, min_length=1, max_length=10_000),
    ) -> PromptResponse:
        try:
            time.sleep(3)
            return PromptResponse(
                status=constants.OK,
                response='Response from LLM based on prompt '+prompt,
            )
        except Exception as exc:
            logger.exception("Unexpected error while processing prompt: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to process prompt request.") from exc


rag_prompt_endpoint = RAGPromptEndpoint()
router = rag_prompt_endpoint.router