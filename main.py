from fastapi import FastAPI

from common import constants
from config.exceptions import exception_handlers
from config.lifespan import lifespan
from config.logger import Logger
from config.middleware import middleware
from config.routes import routes

logger = Logger.get_logger()

def ai_app() -> FastAPI:
    fast_app = FastAPI(
        title=constants.APP_NAME,
        lifespan=lifespan
    )

    @fast_app.get("/")
    @fast_app.get("/health")
    async def health():
        return {"status": "success"}

    exception_handlers(fast_app)
    routes(fast_app)
    middleware(fast_app)

    return fast_app


app = ai_app()