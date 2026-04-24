"""Core exceptions — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.exceptions instead.
"""
from pdftranslator.domain.exceptions.errors import (
    DBConnectionError as ConnectionError,
)
from pdftranslator.domain.exceptions.errors import (  # noqa: F401
    DomainError as DatabaseError,
)
from pdftranslator.domain.exceptions.errors import (
    DuplicateEntityError,
    EntityNotFoundError,
    QueryError,
)

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
]
