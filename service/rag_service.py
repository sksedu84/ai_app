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

            # Retrieve relevant documents from vector database
            relevant_docs = vector_db.search(validated_prompt, k=5)

            if not relevant_docs:
                logger.warning(f"No relevant documents found for prompt: {validated_prompt}")
                context = "No relevant documents found in the knowledge base."
            else:
                # Combine relevant documents into context
                context = "\n---\n".join([
                    f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}"
                    for doc in relevant_docs
                ])

            # Simulate RAG pipeline processing with context
            await asyncio.sleep(3)

            if validated_prompt is None:
                validated_prompt = "Not Valid."

            return PromptResponse(
                status=constants.OK,
                response=validated_prompt,
            )
        except ApplicationError:
            raise
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error while processing RAG prompt: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to process prompt request.") from exc
