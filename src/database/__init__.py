# database/__init__.py
from src.database.models import (
    Work,
    Volume,
    Chapter,
    GlossaryEntry,
    TermContext,
    ContextExample,
)
from src.database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)
from src.database.connection import DatabasePool
from src.database.repositories.book_repository import BookRepository
from src.database.repositories.chapter_repository import ChapterRepository
from src.database.repositories.glossary_repository import GlossaryRepository
from src.database.initializer import DatabaseInitializer

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
