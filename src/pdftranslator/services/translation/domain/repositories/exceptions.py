"""Domain Exceptions for Translation Service."""

from __future__ import annotations


class DomainError(Exception):
    """Base exception for domain rule violations."""
    pass


class NotFoundError(DomainError):
    """Raised when an entity is not found."""
    pass


class ConcurrencyError(DomainError):
    """Raised on optimistic locking conflicts."""
    pass


class ValidationError(DomainError):
    """Raised when input validation fails."""
    pass