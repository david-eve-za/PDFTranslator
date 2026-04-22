"""Domain exceptions package."""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError,
    DBConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

__all__ = [
    "DomainError",
    "DBConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
