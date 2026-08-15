from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from typing import Any, cast

from common import constants
from config.logger import Logger
from model.error_response import ErrorResponse

logger = Logger.get_logger()


class ApplicationError(Exception):
    """Base application error class."""
    
    def __init__(self, message: str, status_code: int = 500):
        """
        Initialize application error.
        
        Args:
            message: Error message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(ApplicationError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class FileError(ApplicationError):
    """Raised when file-related errors."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ProcessingError(ApplicationError):
    """Raised when processing fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


def exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTPException with proper logging and response formatting."""
        request_id = request.headers.get(constants.REQUEST_ID_HEADER)

        logger.warning(
            "HTTP error request_id=%s method=%s path=%s status=%s detail=%s",
            request_id,
            request.method,
            request.url.path,
            exc.status_code,
            exc.detail,
        )

        raw_detail = cast(Any, exc.detail)
        detail_value: str | None = None if raw_detail is None else str(raw_detail)

        payload = ErrorResponse(
            error="Request Failed",
            detail=detail_value,
            request_id=request_id,
        ).model_dump()

        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        """Handle custom application errors."""
        request_id = request.headers.get(constants.REQUEST_ID_HEADER)

        logger.warning(
            "Application error request_id=%s method=%s path=%s status=%s error=%s",
            request_id,
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
        )

        payload = ErrorResponse(
            error="Application Error",
            detail=exc.message,
            request_id=request_id,
        ).model_dump()

        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions with a proper error response."""
        request_id = request.headers.get(constants.REQUEST_ID_HEADER)

        logger.exception(
            "Unhandled error request_id=%s method=%s path=%s error_type=%s",
            request_id,
            request.method,
            request.url.path,
            type(exc).__name__,
        )

        payload = ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred.",
            request_id=request_id,
        ).model_dump()

        return JSONResponse(status_code=500, content=payload)
