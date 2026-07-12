"""
Catalog Service - Main FastAPI Application.

CUPID Principles:
- Composable: Modular routes, dependency injection
- Unix Philosophy: Single responsibility (Catalog API only)
- Predictable: Structured error handling, OpenAPI docs
- Idiomatic: FastAPI best practices, type hints
- Domain-Focused: Rich domain models, repository protocols
"""

from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .config.settings import CatalogSettings
from .infrastructure.database.connection import DatabaseConnection
from .api.routes import works, volumes, chapters
from .api.dependencies import get_database_connection


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = CatalogSettings()
    db = DatabaseConnection(settings)
    await db.connect()
    logger.info("Catalog service started on %s:%s", settings.host, settings.port)

    # Store DB in app state for cleanup
    app.state.db = db

    yield

    # Shutdown
    await db.disconnect()
    logger.info("Catalog service stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = CatalogSettings()

    app = FastAPI(
        title="PDFTranslator Catalog Service",
        description="Catalog API for Works, Volumes, and Chapters",
        version="0.2.0",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Health check endpoints
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "service": "catalog"}

    @app.get("/ready", tags=["health"])
    async def readiness_check():
        db = getattr(app.state, "db", None)
        if db and db.is_connected:
            return {"status": "ready", "database": "connected"}
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": "disconnected"},
        )

    # Include routers
    app.include_router(works.router)
    app.include_router(volumes.router)
    app.include_router(chapters.router)

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = CatalogSettings()
    uvicorn.run(
        "pdftranslator.services.catalog.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=True,
    )