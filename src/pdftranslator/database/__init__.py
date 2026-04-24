# database/__init__.py
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.exceptions import (
    ConnectionError,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
    QueryError,
)
from pdftranslator.database.initializer import DatabaseInitializer
from pdftranslator.database.models import (
    Chapter,
    ContextExample,
    GlossaryEntry,
    TermContext,
    UploadedFile,
    Volume,
    Work,
)
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository

__all__ = [
    "Work",
    "Volume",
    "Chapter",
    "GlossaryEntry",
    "UploadedFile",
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
