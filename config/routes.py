from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

api_router = APIRouter()


def routes(app: FastAPI) -> None:
    from endpoint import admin
    from endpoint import health

    app.include_router(admin.router)
    app.include_router(health.router)

    if not os.path.exists("static"):
        os.makedirs("static")
    
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse("static/favicon.ico")
