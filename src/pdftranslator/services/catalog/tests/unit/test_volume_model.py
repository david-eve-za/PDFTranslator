"""
Unit tests for Volume domain model.
"""

from __future__ import annotations
import pytest
from datetime import datetime

from pdftranslator.services.catalog.domain.models.volume import Volume
from pdftranslator.services.catalog.domain.models.chapter import Chapter
from pdftranslator.services.catalog.domain.repositories.exceptions import DomainError


class TestVolumeModel:
    """Tests for Volume entity."""

    def test_create_valid_volume(self):
        """Should create volume with valid data."""
        volume = Volume(work_id=1, volume_number=1, title="Vol 1")

        assert volume.work_id == 1
        assert volume.volume_number == 1
        assert volume.title == "Vol 1"
        assert volume.glossary_build_status == "pending"

    def test_create_volume_invalid_number_raises(self):
        """Should raise for invalid volume number."""
        with pytest.raises(DomainError, match="positive"):
            Volume(work_id=1, volume_number=0)

        with pytest.raises(DomainError, match="positive"):
            Volume(work_id=1, volume_number=-1)

    def test_create_volume_invalid_work_id_raises(self):
        """Should raise for invalid work_id."""
        with pytest.raises(DomainError, match="valid work"):
            Volume(work_id=0, volume_number=1)

        with pytest.raises(DomainError, match="valid work"):
            Volume(work_id=-1, volume_number=1)

    def test_chapter_management(self):
        """Should manage chapters through aggregate."""
        volume = Volume(work_id=1, volume_number=1)

        ch1 = Chapter(volume_id=1, chapter_number=1, original_text="Chapter 1")
        ch1.set_translation("Translated 1")

        ch2 = Chapter(volume_id=1, chapter_number=2, original_text="Chapter 2")

        volume.add_chapter(ch1)
        volume.add_chapter(ch2)

        assert volume.chapter_count == 2
        assert volume.translated_chapters == 1
        assert volume.translation_progress == 50.0

    def test_duplicate_chapter_number_raises(self):
        """Should raise for duplicate chapter number."""
        volume = Volume(work_id=1, volume_number=1)

        ch1 = Chapter(volume_id=1, chapter_number=1)
        ch2 = Chapter(volume_id=1, chapter_number=1)

        volume.add_chapter(ch1)

        with pytest.raises(DomainError, match="already exists"):
            volume.add_chapter(ch2)

    def test_glossary_status_management(self):
        """Should manage glossary build status."""
        volume = Volume(work_id=1, volume_number=1)

        assert volume.glossary_build_status == "pending"
        assert volume.glossary_built_at is None

        volume.mark_glossary_built()

        assert volume.glossary_build_status == "completed"
        assert volume.glossary_built_at is not None

        volume.mark_glossary_failed("Embedding service unavailable")

        assert volume.glossary_build_status == "failed"
        assert volume.glossary_error_message == "Embedding service unavailable"