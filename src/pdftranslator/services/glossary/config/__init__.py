"""
Glossary Service Configuration.

CUPID Principle: Predictable
- Explicit configuration via environment variables
- Type-safe with Pydantic
- Validated at startup
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class NLTKSettings(BaseSettings):
    """NLTK configuration."""

    data_path: str = Field(
        default="./data/nltk_data",
        description="Path to NLTK data directory",
    )
    download_on_startup: bool = Field(
        default=True,
        description="Auto-download required NLTK packages",
    )

    class Config:
        env_prefix = "NLTK_"


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    provider: str = Field(default="nvidia", description="LLM provider")
    model_name: str = Field(
        default="meta/llama-3.1-70b-instruct",
        description="Model to use for translation",
    )
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    max_tokens: int = Field(default=4096, description="Max tokens per request")
    temperature: float = Field(default=0.1, description="Sampling temperature")
    timeout: float = Field(default=60.0, description="Request timeout")

    class Config:
        env_prefix = "LLM_"
        extra = "allow"


class NVIDIASettings(BaseSettings):
    """NVIDIA NIM specific settings."""

    embed_model: str = Field(
        default="nvidia/nv-embedqa-e5-v5",
        description="Embedding model",
    )
    rerank_model: str = Field(
        default="nvidia/nv-rerankqa-mistral-4b-v3",
        description="Reranking model",
    )
    rerank_top_n: int = Field(default=10, description="Top N for reranking")
    api_key: str = Field(
        default="",
        description="NVIDIA API key (from NVIDIA NIM)",
    )
    max_output_tokens: int = Field(
        default=8192,
        description="Max output tokens for LLM",
    )

    class Config:
        env_prefix = "NVIDIA_"


class GlossarySettings(BaseSettings):
    """Glossary service settings from environment."""

    # Database
    database_path: str = Field(
        default="data/glossary.db",
        description="Path to SQLite database file",
    )

    # API
    host: str = Field(default="0.0.0.0", description="Host to bind")
    port: int = Field(default=8003, description="Port to listen on")
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

    # NLTK
    nltk: NLTKSettings = Field(default_factory=NLTKSettings)

    # LLM
    llm: LLMSettings = Field(default_factory=LLMSettings)
    nvidia: NVIDIASettings = Field(default_factory=NVIDIASettings)

    class Config:
        env_file = ".env"
        env_prefix = "GLOSSARY_"
        case_sensitive = False
        extra = "allow"


# For convenience in code that needs settings
def get_glossary_settings() -> GlossarySettings:
    """Get glossary settings (cached)."""
    from functools import lru_cache

    @lru_cache()
    def _get():
        return GlossarySettings()

    return _get()