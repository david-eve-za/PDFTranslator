# database/repositories/__init__.py
from database.repositories.base import BaseRepository
from database.repositories.book_repository import BookRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from database.repositories.fantasy_term_repository import FantasyTermRepository
from database.repositories.glossary_repository import GlossaryRepository
from database.repositories.volume_repository import VolumeRepository

__all__ = [
    "BaseRepository",
    "BookRepository",
    "ChapterRepository",
    "EntityBlacklistRepository",
    "FantasyTermRepository",
    "GlossaryRepository",
    "VolumeRepository",
]
