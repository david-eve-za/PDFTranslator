"""Domain exceptions — no dependencies on infrastructure.

Resolves DIP-5: core should not depend on database.
Resolves SHD-1: DBConnectionError does not shadow builtin ConnectionError.
"""


class DomainError(Exception):
    """Base exception for all domain errors."""


class DBConnectionError(DomainError):
    """Database connection error."""


class QueryError(DomainError):
    """SQL query error."""


class EntityNotFoundError(DomainError):
    """Entity not found in data store."""


class DuplicateEntityError(DomainError):
    """Entity already exists in data store."""
