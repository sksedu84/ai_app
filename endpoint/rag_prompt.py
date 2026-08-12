from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Depends

from model.prompt_response import PromptResponse
from service.rag_service import RAGServiceImpl


def get_rag_service() -> RAGServiceImpl:
    """Dependency injection for RAGService."""
    return RAGServiceImpl()


class RAGPromptEndpoint:
    """RAG prompt endpoint handler."""
    
    def __init__(self) -> None:
        """Initialize RAG prompt endpoint with routes."""
        self.router = APIRouter(tags=["RAG"], prefix="/rag")

        self.router.add_api_route(
            "",
            self.rag_prompt,
            methods=["GET"],
            response_model=PromptResponse,
        )

    @staticmethod
    async def rag_prompt(
        prompt: str = Query(default=None, min_length=1, max_length=10_000),
        service: Annotated[RAGServiceImpl, Depends(get_rag_service)] = None
    ) -> PromptResponse:
        """
        Process a RAG (Retrieval-Augmented Generation) prompt.
        
        Args:
            prompt: User's prompt/query
            service: Injected RAGService instance
            
        Returns:
            PromptResponse with LLM response
        """
        return await service.process_rag_prompt(prompt)


rag_prompt_endpoint = RAGPromptEndpoint()
router = rag_prompt_endpoint.router