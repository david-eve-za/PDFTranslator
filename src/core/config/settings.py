"""Main application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from src.core.config.llm import LLMSettings, LLMProvider
from src.core.config.database import DatabaseSettings
from src.core.config.nlp import NLPSettings
from src.core.config.paths import PathSettings
from src.core.config.document import DoclingConfig
from src.core.config.processing import ProcessingSettings


class Settings(BaseSettings):
    """
    Main application settings with nested configuration.

    Configuration is loaded from (in order of priority):
    1. Environment variables (highest priority)
    2. .env file
    3. Default values (lowest priority)

    Environment variables use double underscore separator for nested values:
    LLM__AGENT=nvidia
    LLM__NVIDIA__TEMPERATURE=0.5
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Nested configurations
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    nlp: NLPSettings = Field(default_factory=NLPSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    document: DoclingConfig = Field(default_factory=DoclingConfig)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)

    @property
    def agent(self) -> LLMProvider:
        """Convenience property for LLM agent selection."""
        return self.llm.agent


# Module-level singleton for backward compatibility
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """
    Get the singleton settings instance.

    Creates a new instance if one doesn't exist.
    Use reset_settings() to clear the singleton for testing.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    """Reset the singleton instance. Useful for testing."""
    global _settings_instance
    _settings_instance = None


# Add class methods for backward compatibility with plan
Settings.get = staticmethod(get_settings)
Settings.reset = staticmethod(reset_settings)
