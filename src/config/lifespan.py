from contextlib import asynccontextmanager
from fastapi import FastAPI

from config.logger import Logger
from src.common import constants

logger = Logger.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up %s ...", constants.APP_NAME)
    try:
        yield
    finally:
        logger.info("Shutting down %s", constants.APP_NAME)