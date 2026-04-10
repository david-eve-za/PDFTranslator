"""Tests for GlossaryManager auto-batching functionality."""

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


class TestCalculateTranslationBatchSize:
    """Test suite for _calculate_translation_batch_size method."""

    def test_batch_size_calculation(self, glossary_manager):
        """Test batch size is calculated correctly."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        glossary_manager._llm_client = mock_llm

        batch_size = glossary_manager._calculate_translation_batch_size(500)

        # Should be (4096 - 500) / 40 ≈ 90 entities
        assert 80 <= batch_size <= 100

    def test_batch_size_cap(self, glossary_manager):
        """Test batch size is capped at 100."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 10000  # Very high limit
        glossary_manager._llm_client = mock_llm

        batch_size = glossary_manager._calculate_translation_batch_size(1000)

        # Should be capped at 100
        assert batch_size == 100

    def test_batch_size_with_low_limit(self, glossary_manager):
        """Test batch size with low output token limit."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 2048
        glossary_manager._llm_client = mock_llm

        batch_size = glossary_manager._calculate_translation_batch_size(100)

        # Should be smaller with lower limit
        assert 30 <= batch_size <= 50


class TestSplitIntoBatches:
    """Test suite for _split_into_batches method."""

    def test_splits_entities_correctly(self, glossary_manager):
        """Test that entities are split into correct batches."""
        entities = [
            EntityCandidate(text=f"Entity{i}", entity_type="character")
            for i in range(250)
        ]

        batches = glossary_manager._split_into_batches(entities, batch_size=90)

        assert len(batches) == 3
        assert len(batches[0]) == 90
        assert len(batches[1]) == 90
        assert len(batches[2]) == 70

    def test_single_batch_when_fits(self, glossary_manager):
        """Test single batch when entities fit in one batch."""
        entities = [
            EntityCandidate(text=f"Entity{i}", entity_type="character")
            for i in range(50)
        ]

        batches = glossary_manager._split_into_batches(entities, batch_size=100)

        assert len(batches) == 1
        assert len(batches[0]) == 50

    def test_empty_entities(self, glossary_manager):
        """Test handling of empty entity list."""
        batches = glossary_manager._split_into_batches([], batch_size=90)
        assert batches == []


class TestSuggestTranslations:
    """Test suite for _suggest_translations method."""

    def test_uses_validated_translations(self, glossary_manager):
        """Test that validated translations are used directly."""
        mock_llm = MagicMock()
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        glossary_manager._llm_client = mock_llm

        entities = [
            EntityCandidate(
                text="Aria", entity_type="character", translation="Aria", validated=True
            ),
            EntityCandidate(
                text="Dragon",
                entity_type="creature",
                translation="Dragón",
                validated=True,
            ),
        ]

        translations = glossary_manager._suggest_translations(entities, "en", "es")

        assert translations == {"Aria": "Aria", "Dragon": "Dragón"}
        # Should not call LLM
        mock_llm.call_model.assert_not_called()

    def test_batches_large_glossary(self, glossary_manager):
        """Test translation with 500+ entities uses batching."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = (
            '{"Entity0": "Entidad0", "Entity1": "Entidad1"}'
        )
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        glossary_manager._llm_client = mock_llm

        entities = [
            EntityCandidate(text=f"Entity{i}", entity_type="character")
            for i in range(500)
        ]

        translations = glossary_manager._suggest_translations(entities, "en", "es")

        # Should have called LLM multiple times (batched)
        assert mock_llm.call_model.call_count > 1

    def test_handles_translation_error(self, glossary_manager):
        """Test graceful handling of translation errors."""
        mock_llm = MagicMock()
        mock_llm.call_model.side_effect = Exception("API Error")
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        glossary_manager._llm_client = mock_llm

        entities = [
            EntityCandidate(text="Aria", entity_type="character"),
        ]

        # Should return empty dict on error
        translations = glossary_manager._suggest_translations(entities, "en", "es")
        assert translations == {}

    def test_empty_entities(self, glossary_manager):
        """Test handling of empty entity list."""
        translations = glossary_manager._suggest_translations([], "en", "es")
        assert translations == {}


class TestTranslateBatch:
    """Test suite for _translate_batch method."""

    def test_translates_single_batch(self, glossary_manager):
        """Test translation of a single batch."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = '{"Aria": "Aria", "Dragon": "Dragón"}'
        glossary_manager._llm_client = mock_llm

        entities = [
            EntityCandidate(text="Aria", entity_type="character"),
            EntityCandidate(text="Dragon", entity_type="creature"),
        ]

        translations = glossary_manager._translate_batch(entities, "en", "es")

        assert translations == {"Aria": "Aria", "Dragon": "Dragón"}

    def test_strips_json_code_blocks(self, glossary_manager):
        """Test that JSON code blocks are stripped from response."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = """
        ```json
        {"Aria": "Aria"}
        ```
        """
        glossary_manager._llm_client = mock_llm

        entities = [EntityCandidate(text="Aria", entity_type="character")]

        translations = glossary_manager._translate_batch(entities, "en", "es")

        assert translations == {"Aria": "Aria"}

    def test_handles_malformed_json(self, glossary_manager):
        """Test handling of malformed JSON response."""
        mock_llm = MagicMock()
        mock_llm.call_model.return_value = "Not JSON"
        glossary_manager._llm_client = mock_llm

        entities = [EntityCandidate(text="Aria", entity_type="character")]

        translations = glossary_manager._translate_batch(entities, "en", "es")

        # Should return empty dict on JSON error
        assert translations == {}
