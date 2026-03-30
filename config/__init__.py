"""Configuration module using Pydantic Settings."""

from config.settings import Settings
from config.llm import (
    LLMSettings,
    LLMProvider,
    BCP47Language,
    GeminiConfig,
    NvidiaConfig,
    OllamaConfig,
)
from config.database import DatabaseSettings
from config.nlp import NLPSettings
from config.paths import PathSettings

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
