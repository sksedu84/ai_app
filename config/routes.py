from fastapi import APIRouter, FastAPI

api_router = APIRouter()


def routes(app: FastAPI) -> None:
    from endpoint import admin

    app.include_router(admin.router)
