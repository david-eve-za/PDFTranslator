"""Custom exceptions for the application."""

from pdftranslator.database.exceptions import (
    DatabaseError,
    ConnectionError,
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
