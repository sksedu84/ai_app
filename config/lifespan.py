from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

from config.logger import Logger
from common import constants

logger = Logger.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting up %s ...", constants.APP_NAME)
    
    # Ensure required directories exist
    Path(constants.LOG_FILE_DIR).mkdir(parents=True, exist_ok=True)
    Path(constants.DOCUMENT_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(constants.SQL_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path("static").mkdir(parents=True, exist_ok=True)
    
    logger.info("Application directories initialized")
    
    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down %s", constants.APP_NAME)