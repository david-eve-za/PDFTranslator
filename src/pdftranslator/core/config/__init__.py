"""Configuration module using Pydantic Settings."""

from pdftranslator.core.config.settings import Settings
from pdftranslator.core.config.llm import (
    LLMSettings,
    LLMProvider,
    BCP47Language,
    GeminiConfig,
    NvidiaConfig,
    OllamaConfig,
)
from pdftranslator.core.config.database import DatabaseSettings
from pdftranslator.core.config.nlp import NLPSettings
from pdftranslator.core.config.paths import PathSettings

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
