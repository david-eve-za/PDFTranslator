"""Tests that repositories accept pool by injection (DIP-3)."""
from unittest.mock import MagicMock
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository


def test_book_repo_accepts_injected_pool():
    mock_pool = MagicMock()
    repo = BookRepository(pool=mock_pool)
    assert repo._pool is mock_pool


def test_volume_repo_accepts_injected_pool():
    mock_pool = MagicMock()
    repo = VolumeRepository(pool=mock_pool)
    assert repo._pool is mock_pool


def test_chapter_repo_accepts_injected_pool():
    mock_pool = MagicMock()
    repo = ChapterRepository(pool=mock_pool)
    assert repo._pool is mock_pool
