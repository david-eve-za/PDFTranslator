"""
Glossary Service - FastAPI Application Entry Point.

CUPID Principle: Predictable
- Explicit lifespan management
- Health/ready endpoints for container orchestration
- Structured logging
- Dependency injection wired at startup
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config.settings import GlossarySettings, get_glossary_settings
from .api.routes import glossary as glossary_routes
from .api.routes import health as health_routes
from .infrastructure.database.connection import DatabaseConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database connection
_db_connection: DatabaseConnection | None = None


def _get_settings() -> GlossarySettings:
    """Get settings - overrides the imported get_glossary_settings for testing."""
    return get_glossary_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown."""
    global _db_connection

    settings = _get_settings()

    # Startup
    logger.info("Starting Glossary Service...")
    logger.info(f"Database: {settings.database_path}")

    _db_connection = DatabaseConnection(settings)
    await _db_connection.connect()

    logger.info("Glossary Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Glossary Service...")
    if _db_connection:
        await _db_connection.close()
    logger.info("Glossary Service stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = _get_settings()

    app = FastAPI(
        title="PDF Translator - Glossary Service",
        description="Microservice for glossary management and entity extraction",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = __import__("time").time()
        response = await call_next(request)
        process_time = __import__("time").time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.3f}s"
        )
        return response

    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Include routes
    app.include_router(health_routes.router, tags=["health"])
    app.include_router(glossary_routes.router, prefix="/api/v1", tags=["glossary"])

    return app


# Create app instance
app = create_app()


# For direct execution
if __name__ == "__main__":
    import uvicorn

    settings = _get_settings()
    uvicorn.run(
        "src.pdftranslator.services.glossary.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        reload=False,
    )