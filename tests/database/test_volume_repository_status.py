"""Tests for VolumeRepository status methods."""

import pytest
from unittest.mock import MagicMock

from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.connection import DatabasePool


@pytest.fixture
def mock_pool():
    """Mock database pool."""
    pool = MagicMock()
    sync_pool = MagicMock()
    pool.get_sync_pool.return_value = sync_pool
    return pool, sync_pool


@pytest.fixture(autouse=True)
def reset_database_pool():
    """Reset database pool singleton before and after each test."""
    DatabasePool.reset_instance()
    yield
    DatabasePool.reset_instance()


class TestVolumeRepositoryStatus:
    """Tests for glossary build status methods."""

    def test_update_build_status(self, mock_pool):
        """Test updating build status."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.rowcount = 1

        repo = VolumeRepository(pool)
        result = repo.update_build_status(1, "in_progress")

        assert cursor.execute.called
        assert result is True

    def test_update_build_status_with_error(self, mock_pool):
        """Test updating build status with error message."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.rowcount = 1

        repo = VolumeRepository(pool)
        result = repo.update_build_status(1, "failed", error_message="Test error")

        assert cursor.execute.called
        assert result is True

    def test_update_build_status_with_resume_phase(self, mock_pool):
        """Test updating build status with resume phase."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.rowcount = 1

        repo = VolumeRepository(pool)
        result = repo.update_build_status(1, "failed", resume_phase="translation")

        assert cursor.execute.called
        assert result is True

    def test_update_build_status_volume_not_found(self, mock_pool):
        """Test updating build status for non-existent volume."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.rowcount = 0

        repo = VolumeRepository(pool)
        result = repo.update_build_status(999, "in_progress")

        assert cursor.execute.called
        assert result is False

    def test_get_volumes_by_status(self, mock_pool):
        """Test getting volumes by status."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.fetchall.return_value = []

        repo = VolumeRepository(pool)
        result = repo.get_volumes_by_status(1, "failed")

        assert cursor.execute.called
        assert isinstance(result, list)

    def test_get_volumes_by_status_returns_volumes(self, mock_pool):
        """Test that get_volumes_by_status returns Volume objects."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        # Mock data with all 11 columns: id, work_id, volume_number, title, full_text,
        # translated_text, glossary_built_at, created_at, glossary_build_status,
        # glossary_error_message, glossary_resume_phase
        cursor.fetchall.return_value = [
            (1, 1, 1, "Volume 1", None, None, None, None, "pending", None, None),
            (2, 1, 2, "Volume 2", None, None, None, None, "pending", None, None),
        ]

        repo = VolumeRepository(pool)
        result = repo.get_volumes_by_status(1, "pending")

        assert len(result) == 2
        assert result[0].volume_number == 1
        assert result[1].volume_number == 2

    def test_get_volumes_by_status_empty_result(self, mock_pool):
        """Test that get_volumes_by_status returns empty list when no matches."""
        pool, sync_pool = mock_pool
        cursor = MagicMock()
        sync_pool.connection.return_value.__enter__ = MagicMock(return_value=sync_pool)
        sync_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        sync_pool.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        sync_pool.cursor.return_value.__exit__ = MagicMock(return_value=None)
        cursor.fetchall.return_value = []

        repo = VolumeRepository(pool)
        result = repo.get_volumes_by_status(999, "pending")

        assert result == []
