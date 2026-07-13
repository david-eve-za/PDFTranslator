"""
Translation Service Configuration.

CUPID Principle: Predictable
- Explicit configuration via environment variables
- Type-safe with Pydantic
- Validated at startup
"""

from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class TranslationSettings(BaseSettings):
    """Translation service settings from environment."""

    # Database
    database_path: str = Field(
        default="data/translation.db",
        description="Path to SQLite database file",
    )

    # API
    host: str = Field(default="0.0.0.0", description="Host to bind")
    port: int = Field(default=8002, description="Port to listen on")
    workers: int = Field(default=1, description="Number of workers")

    # OpenAPI
    docs_url: str = Field(default="/docs", description="Swagger UI path")
    redoc_url: str = Field(default="/redoc", description="ReDoc path")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI spec path")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json/text)")

    class Config:
        env_file = ".env"
        env_prefix = "TRANSLATION_"
        case_sensitive = False
        extra = "allow"