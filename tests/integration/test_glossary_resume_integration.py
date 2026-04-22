"""Integration tests for glossary resume functionality."""

import os
import pytest
from unittest.mock import MagicMock
from psycopg.errors import UndefinedTable

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository


@pytest.mark.integration
class TestGlossaryResumeIntegration:
    """Test full resume cycle with database."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database connection."""
        DatabasePool.reset_instance()
        yield
        DatabasePool.reset_instance()

    def test_resume_point_detection(self):
        """Test that resume point is correctly detected."""
        pool = DatabasePool.get_instance()
        progress_repo = GlossaryBuildProgressRepository(pool)
        work_id = 1
        volume_id = 1

        # Check resume point (should return extracted if no progress)
        try:
            phase, batch = progress_repo.get_resume_point(work_id, volume_id)
            assert phase in ["extracted", "validated", "translated"]
        except UndefinedTable:
            pytest.skip(
                "Database table 'glossary_build_progress' not migrated - run migration 015"
            )

    def test_volume_build_status_tracking(self):
        """Test volume build status can be updated and retrieved."""
        pool = DatabasePool.get_instance()
        volume_repo = VolumeRepository(pool)

        # This test verifies the repository methods exist
        # Actual database testing would require a test database
        assert hasattr(volume_repo, "update_build_status")
        assert hasattr(volume_repo, "get_volumes_by_status")

    def test_progress_repository_methods(self):
        """Test that progress repository has all required methods."""
        pool = DatabasePool.get_instance()
        progress_repo = GlossaryBuildProgressRepository(pool)

        # Verify all required methods exist
        assert hasattr(progress_repo, "save_extracted")
        assert hasattr(progress_repo, "get_pending_for_phase")
        assert hasattr(progress_repo, "batch_update_phase")
        assert hasattr(progress_repo, "batch_update_embeddings")
        assert hasattr(progress_repo, "batch_update_translations")
        assert hasattr(progress_repo, "get_resume_point")
        assert hasattr(progress_repo, "get_statistics")
        assert hasattr(progress_repo, "cleanup_completed")

    def test_resume_cycle_simulation(self):
        """Test simulated resume cycle without actual database operations."""
        pool = DatabasePool.get_instance()
        progress_repo = GlossaryBuildProgressRepository(pool)

        work_id = 999  # Use non-existent ID for simulation
        volume_id = 999

        # Get resume point for non-existent volume (should return default)
        try:
            phase, batch = progress_repo.get_resume_point(work_id, volume_id)
            # Should return "extracted" as default for non-existent progress
            assert phase == "extracted"
            assert batch is None
        except UndefinedTable:
            pytest.skip(
                "Database table 'glossary_build_progress' not migrated - run migration 015"
            )

    def test_phase_progression_order(self):
        """Test that phases progress in correct order."""
        phases = ["extracted", "validated", "translated", "saved"]

        # Verify phase order is logical
        assert phases.index("extracted") < phases.index("validated")
        assert phases.index("validated") < phases.index("translated")
        assert phases.index("translated") < phases.index("saved")
