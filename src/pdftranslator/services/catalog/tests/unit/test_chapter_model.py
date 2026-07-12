"""
Unit tests for Chapter domain model.
"""

from __future__ import annotations
import pytest
from datetime import datetime

from pdftranslator.services.catalog.domain.models.chapter import Chapter
from pdftranslator.services.catalog.domain.repositories.exceptions import DomainError


class TestChapterModel:
    """Tests for Chapter entity."""

    def test_create_valid_chapter(self):
        """Should create chapter with valid data."""
        chapter = Chapter(volume_id=1, chapter_number=1, title="Ch 1")

        assert chapter.volume_id == 1
        assert chapter.chapter_number == 1
        assert chapter.title == "Ch 1"

    def test_create_chapter_invalid_number_raises(self):
        """Should raise for invalid chapter number."""
        with pytest.raises(DomainError, match="positive"):
            Chapter(volume_id=1, chapter_number=0)

        with pytest.raises(DomainError, match="positive"):
            Chapter(volume_id=1, chapter_number=-1)

    def test_translation_management(self):
        """Should manage translation state."""
        chapter = Chapter(volume_id=1, chapter_number=1, original_text="Original")

        assert chapter.is_translated is False

        chapter.set_translation("Translated")

        assert chapter.is_translated is True
        assert chapter.translated_text == "Translated"

    def test_translation_empty_raises(self):
        """Should raise when setting empty translation."""
        chapter = Chapter(volume_id=1, chapter_number=1)

        with pytest.raises(DomainError, match="Translation cannot be empty"):
            chapter.set_translation("")

    def test_original_text_empty_raises(self):
        """Should raise when setting empty original text."""
        chapter = Chapter(volume_id=1, chapter_number=1)

        with pytest.raises(DomainError, match="Original text cannot be empty"):
            chapter.set_original_text("")

    def test_clear_translation(self):
        """Should clear translation."""
        chapter = Chapter(volume_id=1, chapter_number=1, original_text="O", translated_text="T")

        chapter.clear_translation()

        assert chapter.translated_text is None
        assert chapter.is_translated is False

    def test_word_counts(self):
        """Should calculate word counts correctly."""
        chapter = Chapter(
            volume_id=1,
            chapter_number=1,
            original_text="Hello world test",
            translated_text="Hola mundo prueba",
        )

        assert chapter.word_count_original == 3
        assert chapter.word_count_translated == 3

    def test_update_metadata(self):
        """Should update chapter metadata."""
        chapter = Chapter(volume_id=1, chapter_number=1)
        original_updated = chapter.updated_at

        chapter.update_metadata(title="New Title", chapter_number=2)

        assert chapter.title == "New Title"
        assert chapter.chapter_number == 2
        assert chapter.updated_at > original_updated

    def test_update_chapter_number_invalid_raises(self):
        """Should raise for invalid chapter number."""
        chapter = Chapter(volume_id=1, chapter_number=1)

        with pytest.raises(DomainError, match="positive"):
            chapter.update_metadata(chapter_number=0)