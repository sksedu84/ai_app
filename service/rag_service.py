import asyncio

from fastapi import HTTPException

from common import constants
from common.validate_util import validate_prompt
from common.vector_util import get_vector_db_manager
from config.exceptions import ApplicationError
from config.logger import Logger
from model.prompt_response import PromptResponse
from common.ai_app_util import AiAppUtil

logger = Logger.get_logger()


class RAGServiceImpl:
    def __init__(self):
        pass

    @staticmethod
    async def process_rag_prompt(prompt: str) -> PromptResponse:
        """
        Process a RAG (Retrieval-Augmented Generation) prompt.
        
        Args:
            prompt: The user's prompt/query
            
        Returns:
            PromptResponse with status and LLM response
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            validated_prompt = validate_prompt(prompt)

            # Get vector database manager
            vector_db = get_vector_db_manager()

            # Retrieve relevant documents from vector database
            scored_results = vector_db.search_with_scores(validated_prompt, k=10)

            relevant_docs = [doc for doc, _ in scored_results]

            if not relevant_docs:
                logger.warning(f"No relevant documents found for prompt: {validated_prompt}")


            # Simulate RAG pipeline processing with context
            #await asyncio.sleep(3)
            #response = AiAppUtil.text_to_safe_html(response)

            return PromptResponse(
                status=constants.OK,
                response="response",
            )
        except ApplicationError:
            raise
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error while processing RAG prompt: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to process prompt request.") from exc
