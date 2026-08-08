from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from typing import Any, cast

from common import constants
from config.logger import Logger
from model.error_response import ErrorResponse

logger = Logger.get_logger()


def exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request) -> JSONResponse:
        request_id = request.headers.get(constants.REQUEST_ID_HEADER)

        logger.exception(
            "Unhandled error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        payload = ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred.",
            request_id=request_id,
        ).model_dump()

        return JSONResponse(status_code=500, content=payload)
