from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

api_router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "static"


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

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), check_dir=False), name="static")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        """Serve favicon.ico from a static directory."""
        favicon_path = STATIC_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return Response(status_code=404)
