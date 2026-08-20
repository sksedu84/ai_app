import asyncio
from fastapi import HTTPException

from common import constants
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
            validated_prompt = validate_prompt(prompt)

            # Get vector database manager
            vector_db = get_vector_db_manager()

            # Retrieve candidates with relevance scores.
            similarity_search_results = vector_db.similarity_search(
                validated_prompt,
                k=constants.VECTOR_SEARCH_MAX_K,
            )
            logger.info("Retrieved %d candidate chunks", len(similarity_search_results))

            # Rerank the top results using the reranker model
            reranked_results = vector_db.rerank_documents(
                query=validated_prompt,
                documents=similarity_search_results,
                top_k=constants.RERANK_TOP_K,
            )
            if not reranked_results:
                reranked_results = similarity_search_results[:constants.RERANK_TOP_K]
                logger.warning("Reranker returned no results; using similarity ranking fallback")
            logger.info("Reranked results (top %d): %d", constants.RERANK_TOP_K, len(reranked_results))


            # Simulate RAG pipeline processing with context
            #await asyncio.sleep(3)
            #response = AiAppUtil.text_to_safe_html(response)

            return PromptResponse(
                status=constants.OK,
                response="response",
            )
        except ApplicationError | HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error while processing RAG prompt: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to process prompt request.") from exc
