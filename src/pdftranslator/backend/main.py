"""FastAPI backend application for PDFTranslator."""

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from pdftranslator.core.config.logging import setup_logging
from pdftranslator.core.config.settings import get_settings


# Configure structured logging
settings = get_settings()
setup_logging(settings.log_level)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_startup", version=settings.app_version)

    # Stale job cleanup task would go here
    # For now, just log startup

    yield

    logger.info("application_shutdown")


def custom_generate_unique_id(route: APIRoute) -> str:
    """Generate unique operation IDs for OpenAPI."""
    return f"{route.tags[0] if route.tags else 'default'}-{route.name}"


app = FastAPI(
    title="PDFTranslator API",
    version=settings.app_version,
    description="API for document translation and processing",
    lifespan=lifespan,
    generate_unique_id_function=custom_generate_unique_id,
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to request for distributed tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # Bind correlation ID to structlog context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
from pdftranslator.backend.api.routes import (  # noqa: E402
    chapters,
    files,
    glossary,
    settings as settings_router,
    split,
    substitution_rules,
    translation,
    volumes,
    works,
)

app.include_router(files.router)
app.include_router(glossary.router)
app.include_router(translation.router)
app.include_router(works.router)
app.include_router(volumes.router)
app.include_router(chapters.router)
app.include_router(split.router)
app.include_router(settings_router.router)
app.include_router(substitution_rules.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)