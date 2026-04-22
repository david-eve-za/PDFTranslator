"""Database configuration models."""

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, gt=0, alias="DB_PORT")
    name: str = Field(default="book_translator", alias="DB_NAME")
    user: str = Field(default="translator_user", alias="DB_USER")
    password: str = Field(default="postgres", alias="DB_PASSWORD")
    min_connections: int = Field(default=1, ge=1, alias="DB_MIN_CONNECTIONS")
    max_connections: int = Field(default=10, ge=1, alias="DB_MAX_CONNECTIONS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_connection_string(self) -> str:
        """Build async PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    def __repr__(self) -> str:
        """Safe representation that masks password."""
        return f"DatabaseSettings(host='{self.host}', port={self.port}, name='{self.name}', user='{self.user}', password='***')"
