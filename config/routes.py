from fastapi import APIRouter, FastAPI

api_router = APIRouter()


def routes(app: FastAPI) -> None:
    from endpoint import admin
    from endpoint import health

    app.include_router(admin.router)
    app.include_router(health.router)
