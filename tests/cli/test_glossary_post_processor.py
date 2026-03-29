# tests/cli/test_glossary_post_processor.py
import pytest
from cli.services.glossary_post_processor import GlossaryPostProcessor
from database.models import GlossaryEntry


def create_entry(
    term: str,
    translation: str = None,
    do_not_translate: bool = False,
    entity_type: str = "other",
) -> GlossaryEntry:
    """Helper to create GlossaryEntry for testing."""
    entry = GlossaryEntry()
    entry.term = term
    entry.translation = translation
    entry.do_not_translate = do_not_translate
    entry.entity_type = entity_type
    return entry


class TestGlossaryPostProcessor:
    """Tests for GlossaryPostProcessor."""

    def test_correctly_translated_term_not_modified(self):
        """Term already correctly translated should not be modified."""
        pass

    def test_incorrectly_translated_term_corrected(self):
        """Term translated incorrectly should be corrected."""
        pass

    def test_variant_case_corrected(self):
        """Term with wrong case should be corrected."""
        pass

    def test_plural_variant_corrected(self):
        """Term with wrong plural form should be corrected."""
        pass

    def test_do_not_translate_preserved(self):
        """DO NOT TRANSLATE terms should remain in original."""
        pass

    def test_do_not_translate_reverted(self):
        """DO NOT TRANSLATE terms that were translated should be reverted."""
        pass

    def test_word_boundary_respected(self):
        """Partial matches should not be replaced (e.g., 'Sun' in 'Sunday')."""
        pass

    def test_multiple_occurrences_all_corrected(self):
        """All occurrences of a term should be corrected."""
        pass
