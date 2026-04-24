"""Domain exceptions package."""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DBConnectionError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    QueryError,
)

__all__ = [
    "DomainError",
    "DBConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
