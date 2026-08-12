"""
AI Assistant FastAPI Application

A FastAPI-based application for Retrieval-Augmented Generation (RAG) that allows
users to upload documents, process them, and query an LLM using the documents as context.
"""

from __future__ import annotations

from fastapi import FastAPI

from common import constants
from config.exceptions import exception_handlers
from config.lifespan import lifespan
from config.logger import Logger
from config.middleware import middleware
from config.routes import routes

logger = Logger.get_logger()


def ai_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    fast_app = FastAPI(
        title=constants.APP_NAME,
        description="Retrieval-Augmented Generation (RAG) API",
        version="1.0.0",
        lifespan=lifespan
    )

    # Register exception handlers
    exception_handlers(fast_app)
    
    # Register routes
    routes(fast_app)
    
    # Register middleware
    middleware(fast_app)

    logger.info("FastAPI application configured")
    return fast_app


# Create application instance
app = ai_app()