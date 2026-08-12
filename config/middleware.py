from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, cast
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from common import constants
from config.logger import Logger
from config.settings import settings


def middleware(app: FastAPI) -> None:
    """
    Configure application middleware including CORS and request logging.
    
    Args:
        app: FastAPI application instance
    """
    logger = Logger.get_logger()

    # Configure CORS middleware
    _add_middleware = cast(Any, app.add_middleware)
    _add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=settings.cors_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        allow_credentials=settings.cors_allow_credentials,
    )

    @app.middleware("http")
    async def request_logging(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Middleware for logging HTTP requests and responses.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response with request ID header
        """
        request_id = request.headers.get(constants.REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            assert response is not None
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            status_code = response.status_code if response is not None else "unknown"
            logger.info(
                "method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                request_id,
            )
            if response is not None:
                response.headers[constants.REQUEST_ID_HEADER] = request_id