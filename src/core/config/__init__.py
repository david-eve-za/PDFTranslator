"""Configuration module using Pydantic Settings."""

from src.core.config.settings import Settings
from src.core.config.llm import (
    LLMSettings,
    LLMProvider,
    BCP47Language,
    GeminiConfig,
    NvidiaConfig,
    OllamaConfig,
)
from src.core.config.database import DatabaseSettings
from src.core.config.nlp import NLPSettings
from src.core.config.paths import PathSettings

__all__ = [
    "Settings",
    "LLMSettings",
    "LLMProvider",
    "BCP47Language",
    "GeminiConfig",
    "NvidiaConfig",
    "OllamaConfig",
    "DatabaseSettings",
    "NLPSettings",
    "PathSettings",
]
