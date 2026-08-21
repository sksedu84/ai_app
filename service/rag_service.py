from fastapi import HTTPException

from common import constants
from common.rag_util import RAGUtil
from common.validate_util import validate_prompt
from common.vector_util import get_vector_db_manager
from config.exceptions import ApplicationError
from config.logger import Logger
from model.prompt_response import PromptResponse

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
            # Validate prompt for safety and correctness
            safety_status, validated_prompt = validate_prompt(prompt)
            if safety_status != "safe" or validated_prompt is None:
                return PromptResponse(
                    status=constants.ERROR,
                    response="Prompt validation failed. Please ensure your prompt is safe and valid.",
                )

            # Get vector database manager
            vector_db = get_vector_db_manager()

            # Retrieve candidates directly without reranking.
            similarity_search_results = vector_db.similarity_search(
                validated_prompt,
                k=constants.RAG_CONTEXT_TOP_K,
            )
            logger.info("Retrieved %d candidate chunks", len(similarity_search_results))

            # Generate a RAG response from the local LLM using the retrieved context
            response = await RAGUtil.generate(
                question=validated_prompt,
                documents=similarity_search_results,
            )

            return PromptResponse(
                status=constants.OK,
                response=response,
            )
        except ApplicationError | HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error while processing RAG prompt: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to process prompt request.") from exc
