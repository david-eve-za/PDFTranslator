# database/__init__.py
from database.models import (
    Work,
    Volume,
    Chapter,
    GlossaryEntry,
    TermContext,
    ContextExample,
)
from database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)
from database.connection import DatabasePool
from database.repositories.book_repository import BookRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.glossary_repository import GlossaryRepository
from database.initializer import DatabaseInitializer

__all__ = [
    "Work",
    "Volume",
    "Chapter",
    "GlossaryEntry",
    "TermContext",
    "ContextExample",
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "DatabasePool",
    "BookRepository",
    "ChapterRepository",
    "GlossaryRepository",
    "DatabaseInitializer",
]
