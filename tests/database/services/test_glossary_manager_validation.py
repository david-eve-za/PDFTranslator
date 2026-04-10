"""Tests for GlossaryManager LLM validation functionality."""

import pytest
from unittest.mock import MagicMock, patch
from pdftranslator.database.models import EntityCandidate
from pdftranslator.database.services.glossary_manager import GlossaryManager


@pytest.fixture
def mock_pool():
    """Mock database pool."""
    return MagicMock()


@pytest.fixture
def glossary_manager(mock_pool):
    """Create GlossaryManager with mocked dependencies."""
    with (
        patch("pdftranslator.database.services.glossary_manager.EntityExtractor"),
        patch("pdftranslator.database.services.glossary_manager.GlossaryRepository"),
        patch("pdftranslator.database.services.glossary_manager.VectorStoreService"),
    ):
        manager = GlossaryManager(mock_pool)
        return manager


class TestValidateWithLLM:
    """Test suite for _validate_with_llm method."""

    def test_filters_false_positives(self, glossary_manager):
        """Test that LLM validation filters out common words."""
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = """
        ```json
        {
            "entities": [
                {"text": "The", "valid": false, "type": null, "suggest": null},
                {"text": "Aria", "valid": true, "type": "character", "suggest": "Aria"}
            ]
        }
        ```
        """
        glossary_manager._llm_client = mock_llm
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096

        entities = [
            EntityCandidate(
                text="The", entity_type="character", contexts=["The dragon..."]
            ),
            EntityCandidate(
                text="Aria",
                entity_type="character",
                contexts=["Aria drew her sword..."],
            ),
        ]

        validated = glossary_manager._validate_with_llm(entities, "en")

        assert len(validated) == 1
        assert validated[0].text == "Aria"
        assert validated[0].validated is True
        assert validated[0].entity_type == "character"

    def test_improves_classification(self, glossary_manager):
        """Test that LLM improves entity type classification."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = """
        ```json
        {
            "entities": [
                {"text": "Fireball", "valid": true, "type": "skill", "suggest": "Bola de Fuego"}
            ]
        }
        ```
        """
        glossary_manager._llm_client = mock_llm
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096

        entities = [
            EntityCandidate(
                text="Fireball", entity_type="other", contexts=["cast Fireball..."]
            ),
        ]

        validated = glossary_manager._validate_with_llm(entities, "en")

        assert len(validated) == 1
        assert validated[0].entity_type == "skill"
        assert validated[0].translation == "Bola de Fuego"

    def test_provides_initial_translations(self, glossary_manager):
        """Test that LLM provides initial translations during validation."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = """
        ```json
        {
            "entities": [
                {"text": "Shadowmere", "valid": true, "type": "place", "suggest": "Sombraña"}
            ]
        }
        ```
        """
        glossary_manager._llm_client = mock_llm
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096

        entities = [
            EntityCandidate(
                text="Shadowmere",
                entity_type="place",
                contexts=["Shadowmere forest..."],
            ),
        ]

        validated = glossary_manager._validate_with_llm(entities, "en")

        assert len(validated) == 1
        assert validated[0].translation == "Sombraña"

    def test_handles_json_decode_error(self, glossary_manager):
        """Test graceful handling of malformed JSON response."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = "This is not valid JSON"
        glossary_manager._llm_client = mock_llm
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096

        entities = [
            EntityCandidate(text="Aria", entity_type="character", contexts=["Aria..."]),
        ]

        # Should return original entities on error
        validated = glossary_manager._validate_with_llm(entities, "en")
        assert len(validated) == 1

    def test_empty_entities(self, glossary_manager):
        """Test handling of empty entity list."""
        validated = glossary_manager._validate_with_llm([], "en")
        assert validated == []


class TestCalculateValidationBatchSize:
    """Test suite for _calculate_validation_batch_size method."""

    def test_batch_size_calculation(self, glossary_manager):
        """Test batch size is calculated correctly."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        glossary_manager._llm_client = mock_llm

        batch_size = glossary_manager._calculate_validation_batch_size()

        # Should be (4096 - 500) / 60 ≈ 60 entities
        assert 50 <= batch_size <= 80

    def test_batch_size_with_higher_limit(self, glossary_manager):
        """Test batch size is capped at 80."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 8192
        glossary_manager._llm_client = mock_llm

        batch_size = glossary_manager._calculate_validation_batch_size()

        # Should be capped at 80 (validation cap)
        assert batch_size == 80


class TestValidateBatch:
    """Test suite for _validate_batch method."""

    def test_validates_single_batch(self, glossary_manager):
        """Test validation of a single batch."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = """
        {
            "entities": [
                {"text": "Aria", "valid": true, "type": "character", "suggest": "Aria"},
                {"text": "Dragon", "valid": true, "type": "creature", "suggest": "Dragón"}
            ]
        }
        """
        glossary_manager._llm_client = mock_llm

        entities = [
            EntityCandidate(text="Aria", entity_type="character", contexts=["Aria..."]),
            EntityCandidate(text="Dragon", entity_type="other", contexts=["Dragon..."]),
        ]

        validated = glossary_manager._validate_batch(entities, "en")

        assert len(validated) == 2
        assert validated[0].validated is True
        assert validated[1].entity_type == "creature"
