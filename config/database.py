"""Database configuration models."""

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Database connection settings."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432, gt=0)
    name: str = Field(default="pdftranslator")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    min_connections: int = Field(default=1, ge=1)
    max_connections: int = Field(default=10, ge=1)

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_connection_string(self) -> str:
        """Build async PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
