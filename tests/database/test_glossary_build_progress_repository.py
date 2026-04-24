"""Tests for GlossaryBuildProgressRepository."""

import pytest
from unittest.mock import MagicMock, patch

from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)
from pdftranslator.database.models import EntityCandidate, GlossaryBuildProgress


@pytest.fixture
def mock_pool():
    """Mock database pool."""
    return MagicMock()


@pytest.fixture
def mock_connection():
    """Mock database connection and cursor."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@pytest.fixture
def sample_entities():
    """Sample entity candidates for testing."""
    return [
        EntityCandidate(text="Harry Potter", entity_type="character", frequency=10),
        EntityCandidate(text="Hogwarts", entity_type="place", frequency=5),
        EntityCandidate(text="Expelliarmus", entity_type="skill", frequency=3),
    ]


class TestGlossaryBuildProgressRepository:
    def test_save_extracted(self, mock_pool, mock_connection, sample_entities):
        """Test saving extracted entities."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.fetchone.return_value = (
            1,
            1,
            1,
            "Harry Potter",
            "extracted",
            "character",
            10,
            [],
            None,
            None,
            None,
            None,
            None,
            None,
        )

        repo = GlossaryBuildProgressRepository(mock_pool)
        result = repo.save_extracted(1, 1, sample_entities)

        assert cursor.execute.called
        assert len(result) >= 0

    def test_get_pending_for_phase(self, mock_pool, mock_connection):
        """Test retrieving pending entities for a phase."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.fetchall.return_value = [
            (
                1,
                1,
                1,
                "Harry Potter",
                "extracted",
                "character",
                10,
                [],
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]

        repo = GlossaryBuildProgressRepository(mock_pool)
        result = repo.get_pending_for_phase(1, 1, "extracted")

        assert len(result) == 1
        assert result[0].entity_text == "Harry Potter"
        assert result[0].phase == "extracted"

    def test_batch_update_phase(self, mock_pool, mock_connection):
        """Test batch updating phase."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.rowcount = 3

        repo = GlossaryBuildProgressRepository(mock_pool)
        result = repo.batch_update_phase([1, 2, 3], "validated")

        assert cursor.execute.called
        assert result == 3

    def test_get_resume_point_empty(self, mock_pool, mock_connection):
        """Test resume point when no progress exists."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.fetchall.return_value = []

        repo = GlossaryBuildProgressRepository(mock_pool)
        phase, batch = repo.get_resume_point(1, 1)

        assert phase == "extracted"
        assert batch is None

    def test_get_statistics(self, mock_pool, mock_connection):
        """Test getting progress statistics."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.fetchall.return_value = [
            ("extracted", 10),
            ("validated", 5),
            ("saved", 3),
        ]

        repo = GlossaryBuildProgressRepository(mock_pool)
        result = repo.get_statistics(1, 1)

        assert result["extracted"] == 10
        assert result["validated"] == 5
        assert result["saved"] == 3

    def test_cleanup_completed(self, mock_pool, mock_connection):
        """Test cleaning up completed progress."""
        conn, cursor = mock_connection
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=conn)
        )
        mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = (
            MagicMock(return_value=None)
        )
        cursor.rowcount = 10

        repo = GlossaryBuildProgressRepository(mock_pool)
        result = repo.cleanup_completed(1)

        assert cursor.execute.called
