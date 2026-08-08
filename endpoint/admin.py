from typing import List

from fastapi import APIRouter, UploadFile, File

from config.logger import Logger
from model.admin_response import AdminResponse
from service.admin_service import AdminServiceImpl

logger = Logger.get_logger()


class AdminEndpoint:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["Admin"])

        self.router.add_api_route(
            "/admin",
            self.admin,
            methods=["GET"],
            response_model=AdminResponse,
        )

        self.router.add_api_route(
            "/admin/upload-files",
            self.upload_files,
            methods=["POST"],
            response_model=AdminResponse,
        )

    @staticmethod
    async def admin():
        return await AdminServiceImpl.admin()

    @staticmethod
    async def upload_files(files: List[UploadFile] = File(...)):
        return await AdminServiceImpl.upload_files(files)

admin_endpoint = AdminEndpoint()
router = admin_endpoint.router
