"""
Unit tests for Work domain model.

CUPID Principle: Predictable
- Tests domain invariants
- Tests business behavior
- No infrastructure dependencies
"""

from __future__ import annotations
import pytest
from datetime import datetime

from pdftranslator.services.catalog.domain.models.work import Work
from pdftranslator.services.catalog.domain.models.volume import Volume
from pdftranslator.services.catalog.domain.models.chapter import Chapter
from pdftranslator.services.catalog.domain.repositories.exceptions import DomainError


class TestWorkModel:
    """Tests for Work aggregate root."""

    def test_create_valid_work(self):
        """Should create work with valid data."""
        work = Work(
            title="Test Book",
            source_lang="en",
            target_lang="es",
            author="Test Author",
        )

        assert work.title == "Test Book"
        assert work.source_lang == "en"
        assert work.target_lang == "es"
        assert work.author == "Test Author"
        assert work.uuid is not None
        assert work.created_at is not None

    def test_create_work_empty_title_raises(self):
        """Should raise DomainError for empty title."""
        with pytest.raises(DomainError, match="title cannot be empty"):
            Work(title="", source_lang="en", target_lang="es")

    def test_create_work_whitespace_title_raises(self):
        """Should raise DomainError for whitespace-only title."""
        with pytest.raises(DomainError, match="title cannot be empty"):
            Work(title="   ", source_lang="en", target_lang="es")

    def test_create_work_invalid_source_lang_raises(self):
        """Should raise DomainError for invalid source language."""
        with pytest.raises(DomainError, match="ISO 639-1"):
            Work(title="Test", source_lang="eng", target_lang="es")

    def test_create_work_invalid_target_lang_raises(self):
        """Should raise DomainError for invalid target language."""
        with pytest.raises(DomainError, match="ISO 639-1"):
            Work(title="Test", source_lang="en", target_lang="spa")

    def test_create_work_same_lang_raises(self):
        """Should raise DomainError when source equals target."""
        with pytest.raises(DomainError, match="must differ"):
            Work(title="Test", source_lang="en", target_lang="en")

    def test_update_metadata_valid(self):
        """Should update metadata with valid values."""
        work = Work(title="Original", source_lang="en", target_lang="es")
        original_updated = work.updated_at

        work.update_metadata(title="Updated Title", author="New Author")

        assert work.title == "Updated Title"
        assert work.author == "New Author"
        assert work.updated_at > original_updated

    def test_update_metadata_empty_title_raises(self):
        """Should raise when updating to empty title."""
        work = Work(title="Original", source_lang="en", target_lang="es")

        with pytest.raises(DomainError, match="title cannot be empty"):
            work.update_metadata(title="")

    def test_volume_management(self):
        """Should manage volumes through aggregate."""
        work = Work(title="Test", source_lang="en", target_lang="es")
        volume = Volume(
            work_id=1,
            volume_number=1,
            title="Volume 1",
        )

        work.add_volume(volume)

        assert work.volume_count == 1
        assert work.get_volume(1) == volume
        assert volume.work_id == 1

    def test_duplicate_volume_number_raises(self):
        """Should raise when adding duplicate volume number."""
        work = Work(title="Test", source_lang="en", target_lang="es")

        vol1 = Volume(work_id=1, volume_number=1)
        vol2 = Volume(work_id=1, volume_number=1)

        work.add_volume(vol1)

        with pytest.raises(DomainError, match="already exists"):
            work.add_volume(vol2)

    def test_translation_progress_calculation(self):
        """Should calculate translation progress correctly."""
        work = Work(title="Test", source_lang="en", target_lang="es")

        vol = Volume(work_id=1, volume_number=1)

        ch1 = Chapter(volume_id=1, chapter_number=1, original_text="Hello world")
        ch1.set_translation("Hola mundo")

        ch2 = Chapter(volume_id=1, chapter_number=2, original_text="Goodbye")

        vol.add_chapter(ch1)
        vol.add_chapter(ch2)
        work.add_volume(vol)

        assert work.total_chapters == 2
        assert work.translated_chapters == 1
        assert work.translation_progress == 50.0

    def test_remove_volume(self):
        """Should remove volume by number."""
        work = Work(title="Test", source_lang="en", target_lang="es")
        vol = Volume(work_id=1, volume_number=1)
        work.add_volume(vol)

        result = work.remove_volume(1)

        assert result is True
        assert work.volume_count == 0
        assert work.get_volume(1) is None