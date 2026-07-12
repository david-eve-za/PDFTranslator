"""Database configuration models for SQLite."""

from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """SQLite database connection settings."""

    path: Path = Field(
        default=Path("data/translator.db"),
        validation_alias=AliasChoices("DB_PATH", "SQLITE_PATH", "DATABASE_PATH"),
    )
    journal_mode: str = Field(default="WAL", alias="DB_JOURNAL_MODE")
    synchronous: str = Field(default="NORMAL", alias="DB_SYNCHRONOUS")
    cache_size: int = Field(default=-32768, alias="DB_CACHE_SIZE")
    temp_store: str = Field(default="MEMORY", alias="DB_TEMP_STORE")
    busy_timeout: int = Field(default=5000, alias="DB_BUSY_TIMEOUT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def connection_string(self) -> str:
        """Build SQLite connection string."""
        return f"sqlite:///{self.path}"

    @property
    def async_connection_string(self) -> str:
        """Build async SQLite connection string."""
        return f"sqlite+aiosqlite:///{self.path}"

    def __repr__(self) -> str:
        """Safe representation."""
        return f"DatabaseSettings(path='{self.path}')"