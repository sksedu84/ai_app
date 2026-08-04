from fastapi import APIRouter

api_router = APIRouter()


def routes(router: APIRouter) -> None:
    from endpoint import admin

    router.include_router(admin.router)


routes(api_router)