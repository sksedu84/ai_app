from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, UploadFile, File, Depends

from config.logger import Logger
from model.admin_response import AdminResponse
from service.admin_service import AdminServiceImpl

logger = Logger.get_logger()


def get_admin_service() -> AdminServiceImpl:
    """Dependency injection for AdminService."""
    return AdminServiceImpl()


class AdminEndpoint:
    """Admin endpoint handler."""
    
    def __init__(self) -> None:
        """Initialize admin endpoint with routes."""
        self.router = APIRouter(tags=["Admin"], prefix="/admin")

        self.router.add_api_route(
            "",
            self.admin,
            methods=["GET"],
            response_model=AdminResponse,
        )

        self.router.add_api_route(
            "/upload-files",
            self.upload_files,
            methods=["POST"],
            response_model=AdminResponse,
        )

        self.router.add_api_route(
            "/document/embeddings",
            self.document_embeddings,
            methods=["GET"],
            response_model=AdminResponse,
        )

    @staticmethod
    async def admin(
        service: Annotated[AdminServiceImpl, Depends(get_admin_service)]
    ) -> AdminResponse:
        """
        Get an admin dashboard with an uploaded files list.
        
        Args:
            service: Injected AdminService instance
            
        Returns:
            AdminResponse with a file list
        """
        return await service.admin()

    @staticmethod
    async def upload_files(
        service: Annotated[AdminServiceImpl, Depends(get_admin_service)],
        files: list[UploadFile] = File(...),
    ) -> AdminResponse:
        """
        Upload files to the application.
        
        Args:
            files: List of files to upload
            service: Injected AdminService instance
            
        Returns:
            AdminResponse confirming upload
        """
        return await service.upload_files(files)

    @staticmethod
    async def document_embeddings(
            service: Annotated[AdminServiceImpl, Depends(get_admin_service)]
    ) -> AdminResponse:
        """
        Ingest documents and update embeddings.

        Args:
            service: Injected AdminService instance

        Returns:
            AdminResponse confirming document embeddings update
        """
        return await service.document_embeddings()


admin_endpoint = AdminEndpoint()
router = admin_endpoint.router
