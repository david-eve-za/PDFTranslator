# database/__init__.py
from pdftranslator.database.models import (
    Work,
    Volume,
    Chapter,
    GlossaryEntry,
    TermContext,
    ContextExample,
)
from pdftranslator.database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.initializer import DatabaseInitializer

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
