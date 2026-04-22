"""Tests for GlossaryManager progress tracking."""

import pytest
from unittest.mock import MagicMock, patch

from pdftranslator.database.models import EntityCandidate, GlossaryBuildProgress
from pdftranslator.database.services.glossary_manager import GlossaryManager


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies."""
    with (
        patch(
            "pdftranslator.database.services.glossary_manager.EntityExtractor"
        ) as mock_extractor_cls,
        patch(
            "pdftranslator.database.services.glossary_manager.GlossaryRepository"
        ) as mock_glossary_cls,
        patch(
            "pdftranslator.database.services.glossary_manager.GlossaryBuildProgressRepository"
        ) as mock_progress_cls,
        patch(
            "pdftranslator.database.services.glossary_manager.VectorStoreService"
        ) as mock_vector_cls,
    ):
        mock_pool = MagicMock()
        mock_extractor = MagicMock()
        mock_glossary = MagicMock()
        mock_progress = MagicMock()
        mock_vector = MagicMock()

        mock_extractor_cls.return_value = mock_extractor
        mock_glossary_cls.return_value = mock_glossary
        mock_progress_cls.return_value = mock_progress
        mock_vector_cls.return_value = mock_vector

        yield {
            "pool": mock_pool,
            "extractor": mock_extractor,
            "glossary": mock_glossary,
            "progress": mock_progress,
            "vector": mock_vector,
        }


class TestGlossaryManagerProgress:
    def test_save_extracted_on_build(self, mock_dependencies):
        """Test that extracted entities are saved to progress table."""
        manager = GlossaryManager(mock_dependencies["pool"])

        mock_dependencies["extractor"].extract.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]

        mock_dependencies["glossary"].filter_new_entities.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]

        # Return a progress record
        progress_record = GlossaryBuildProgress(
            id=1,
            work_id=1,
            volume_id=1,
            entity_text="Harry",
            phase="extracted",
            entity_type="character",
            frequency=5,
        )
        mock_dependencies["progress"].save_extracted.return_value = [progress_record]

        mock_dependencies["vector"].embed_entities_for_glossary.return_value = []

        result = manager.build_from_text(
            text="Test text",
            work_id=1,
            volume_id=1,
            suggest_translations=False,
        )

        # Verify save_extracted was called with correct params
        mock_dependencies["progress"].save_extracted.assert_called_once()
        call_args = mock_dependencies["progress"].save_extracted.call_args
        assert call_args[0][0] == 1  # work_id
        assert call_args[0][1] == 1  # volume_id
        assert len(call_args[0][2]) == 1  # entities list

    def test_cleanup_on_completion(self, mock_dependencies):
        """Test that progress is cleaned up after successful completion."""
        manager = GlossaryManager(mock_dependencies["pool"])

        mock_dependencies["extractor"].extract.return_value = []
        mock_dependencies["glossary"].filter_new_entities.return_value = []

        result = manager.build_from_text(
            text="Test",
            work_id=1,
            volume_id=1,
        )

        # When no entities, cleanup should still be called
        mock_dependencies["progress"].cleanup_completed.assert_called_once_with(1)

    def test_cleanup_with_entities(self, mock_dependencies):
        """Test cleanup is called after saving entities."""
        manager = GlossaryManager(mock_dependencies["pool"])

        mock_dependencies["extractor"].extract.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]

        mock_dependencies["glossary"].filter_new_entities.return_value = [
            EntityCandidate(text="Harry", entity_type="character", frequency=5),
        ]

        progress_record = GlossaryBuildProgress(
            id=1,
            work_id=1,
            volume_id=1,
            entity_text="Harry",
            phase="extracted",
            entity_type="character",
            frequency=5,
        )
        mock_dependencies["progress"].save_extracted.return_value = [progress_record]
        mock_dependencies["progress"].batch_update_phase.return_value = 1

        # Mock embedding result
        mock_dependencies["vector"].embed_entities_for_glossary.return_value = [
            (
                EntityCandidate(text="Harry", entity_type="character", frequency=5),
                [0.1] * 1024,
            ),
        ]

        # Mock glossary save
        mock_dependencies["glossary"].batch_create_with_embeddings.return_value = []

        result = manager.build_from_text(
            text="Test text",
            work_id=1,
            volume_id=1,
            suggest_translations=False,
        )

        # Verify batch_update_phase was called with 'saved' phase
        mock_dependencies["progress"].batch_update_phase.assert_called_once()
        call_args = mock_dependencies["progress"].batch_update_phase.call_args
        assert call_args[0][1] == "saved"  # phase

        # Verify cleanup was called
        mock_dependencies["progress"].cleanup_completed.assert_called_once_with(1)

    def test_resume_from_validation_phase(self, mock_dependencies):
        """Test resuming from validation phase."""
        manager = GlossaryManager(mock_dependencies["pool"])

        # Mock resume point detection
        mock_dependencies["progress"].get_resume_point.return_value = ("validated", 2)

        # Mock pending entities
        mock_progress = MagicMock()
        mock_progress.id = 1
        mock_progress.entity_text = "Harry"
        mock_progress.entity_type = "character"
        mock_progress.frequency = 5
        mock_progress.contexts = []
        mock_progress.translation = None
        mock_dependencies["progress"].get_pending_for_phase.return_value = [
            mock_progress
        ]

        # Mock embedding and save
        mock_dependencies["vector"].embed_entities_for_glossary.return_value = [
            (
                EntityCandidate(text="Harry", entity_type="character", frequency=5),
                [0.1] * 1024,
            )
        ]
        mock_dependencies["glossary"].batch_create_with_embeddings.return_value = []

        # Call with resume=True
        result = manager.build_from_text(
            text="Test",
            work_id=1,
            volume_id=1,
            resume=True,
            suggest_translations=False,
        )

        # Should not call extractor when resuming
        mock_dependencies["extractor"].extract.assert_not_called()

        # Should have called get_pending_for_phase with "extracted" phase
        mock_dependencies["progress"].get_pending_for_phase.assert_called()

        # Should have called batch_update_phase with "saved"
        mock_dependencies["progress"].batch_update_phase.assert_called()

    def test_resume_from_translated_phase(self, mock_dependencies):
        """Test resuming from translation phase."""
        manager = GlossaryManager(mock_dependencies["pool"])

        # Mock resume point detection - translation already done
        mock_dependencies["progress"].get_resume_point.return_value = ("translated", 3)

        # Mock pending entities with translations
        mock_progress = MagicMock()
        mock_progress.id = 1
        mock_progress.entity_text = "Harry"
        mock_progress.entity_type = "character"
        mock_progress.frequency = 5
        mock_progress.contexts = []
        mock_progress.translation = "Harry"
        mock_dependencies["progress"].get_pending_for_phase.return_value = [
            mock_progress
        ]

        # Mock embedding and save
        mock_dependencies["vector"].embed_entities_for_glossary.return_value = [
            (
                EntityCandidate(
                    text="Harry",
                    entity_type="character",
                    frequency=5,
                    translation="Harry",
                ),
                [0.1] * 1024,
            )
        ]
        mock_dependencies["glossary"].batch_create_with_embeddings.return_value = []

        result = manager.build_from_text(
            text="Test",
            work_id=1,
            volume_id=1,
            resume=True,
            suggest_translations=False,
        )

        # Should not call extractor when resuming
        mock_dependencies["extractor"].extract.assert_not_called()

        # Should have saved the entities
        mock_dependencies["glossary"].batch_create_with_embeddings.assert_called_once()
