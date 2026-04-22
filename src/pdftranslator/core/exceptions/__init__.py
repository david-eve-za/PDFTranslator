"""Core exceptions — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.exceptions instead.
"""
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError as DatabaseError,
    DBConnectionError as ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
