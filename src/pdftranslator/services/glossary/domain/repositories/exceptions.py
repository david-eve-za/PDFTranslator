"""
Domain exceptions for Glossary Service.

CUPID Principle: Predictable
- Explicit domain errors
- No infrastructure leakage
"""

from __future__ import annotations


class DomainError(Exception):
    """Base domain exception."""
    pass


class NotFoundError(DomainError):
    """Entity not found."""
    pass


class DuplicateError(DomainError):
    """Duplicate entity violation."""
    pass


class ValidationError(DomainError):
    """Domain validation failed."""
    pass


class InvalidStateError(DomainError):
    """Invalid state transition."""
    pass


class PipelineError(DomainError):
    """Pipeline operation failed."""
    pass


class EntityNotValidError(ValidationError):
    """Entity failed validation."""
    pass


class GlossaryNotFoundError(NotFoundError):
    """Glossary not found."""
    pass


class PipelineNotFoundError(NotFoundError):
    """Build pipeline not found."""
    pass


class EntityCandidateNotFoundError(NotFoundError):
    """Entity candidate not found."""
    pass


class InsufficientContextError(ValidationError):
    """Not enough context for translation."""
    pass


class LLMError(PipelineError):
    """LLM service error."""
    pass


class EmbeddingError(PipelineError):
    """Embedding generation error."""
    pass


class ConcurrencyError(DomainError):
    """Optimistic locking conflict."""
    pass