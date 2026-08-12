from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from common import constants

router = APIRouter(tags=["Health"])


class HealthEndpoint:
    """Health check endpoint handler."""
    
    def __init__(self) -> None:
        """Initialize health endpoint."""
        pass

    @staticmethod
    async def get() -> JSONResponse:
        """
        Get application health status.
        
        Returns:
            JSONResponse with health status
        """
        return JSONResponse(
            status_code=200,
            content={
                "status": constants.OK,
                "service": constants.APP_NAME,
            },
        )


# Add routes to router
router.add_api_route("/", HealthEndpoint.get, methods=["GET"], response_class=JSONResponse, include_in_schema=False)
router.add_api_route("/health", HealthEndpoint.get, methods=["GET"], response_class=JSONResponse)
