from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

api_router = APIRouter()


def _ensure_static_files() -> None:
    """Ensure a static files directory exists."""
    static_dir = Path("static")
    if not static_dir.exists():
        static_dir.mkdir(parents=True, exist_ok=True)
        favicon_path = static_dir / "favicon.ico"
        if not favicon_path.exists():
            favicon_path.touch()


def routes(app: FastAPI) -> None:
    """
    Configure application routes and static file serving.
    
    Args:
        app: FastAPI application instance
    """
    from endpoint import admin
    from endpoint import health
    from endpoint import rag_prompt

    # Include routers
    app.include_router(admin.router)
    app.include_router(health.router)
    app.include_router(rag_prompt.router)

    # Ensure static files directory exists
    _ensure_static_files()
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        """Serve favicon.ico from a static directory."""
        favicon_path = Path("static") / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        # Return 404 if favicon doesn't exist
        return FileResponse(status_code=404)
