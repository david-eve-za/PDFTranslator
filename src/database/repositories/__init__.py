# database/repositories/__init__.py
from src.database.repositories.base import BaseRepository
from src.database.repositories.book_repository import BookRepository
from src.database.repositories.chapter_repository import ChapterRepository
from src.database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from src.database.repositories.fantasy_term_repository import FantasyTermRepository
from src.database.repositories.glossary_repository import GlossaryRepository
from src.database.repositories.volume_repository import VolumeRepository

__all__ = [
    "BaseRepository",
    "BookRepository",
    "ChapterRepository",
    "EntityBlacklistRepository",
    "FantasyTermRepository",
    "GlossaryRepository",
    "VolumeRepository",
]
