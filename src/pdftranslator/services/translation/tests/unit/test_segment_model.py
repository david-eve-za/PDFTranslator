"""
Unit tests for Segment domain model.

CUPID Principle: Predictable
- Tests domain invariants
- Tests translation management
- No infrastructure dependencies
"""

from __future__ import annotations
import pytest

from pdftranslator.services.translation.domain.models.segment import Segment
from pdftranslator.services.translation.domain.repositories.exceptions import DomainError


class TestSegment:
    """Tests for Segment entity."""

    def test_create_valid_segment(self):
        """Should create segment with valid data."""
        segment = Segment(
            job_id=1,
            segment_number=1,
            source_text="Hello world",
        )

        assert segment.job_id == 1
        assert segment.segment_number == 1
        assert segment.source_text == "Hello world"
        assert segment.target_text is None
        assert segment.context_before is None
        assert segment.context_after is None
        assert segment.notes is None
        assert segment.is_translated is False
        assert segment.uuid is not None

    def test_create_segment_invalid_number_raises(self):
        """Should raise for invalid segment number."""
        with pytest.raises(DomainError, match="positive"):
            Segment(job_id=1, segment_number=0)

        with pytest.raises(DomainError, match="positive"):
            Segment(job_id=1, segment_number=-1)

    def test_set_translation(self):
        """Should set translation text."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")
        assert segment.is_translated is False

        segment.set_translation("Hola")

        assert segment.target_text == "Hola"
        assert segment.is_translated is True

    def test_set_translation_updates_timestamp(self):
        """Should update updated_at when setting translation."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")
        original_updated = segment.updated_at

        segment.set_translation("Hola")

        assert segment.updated_at > original_updated

    def test_set_empty_translation_raises(self):
        """Should raise when setting empty translation."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")

        with pytest.raises(DomainError, match="Translation cannot be empty"):
            segment.set_translation("")

        with pytest.raises(DomainError, match="Translation cannot be empty"):
            segment.set_translation("   ")

    def test_clear_translation(self):
        """Should clear translation."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello", target_text="Hola")

        segment.clear_translation()

        assert segment.target_text is None
        assert segment.is_translated is False

    def test_set_context(self):
        """Should set context before and after."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")

        segment.set_context(before="Previous text.", after="Next text.")

        assert segment.context_before == "Previous text."
        assert segment.context_after == "Next text."

    def test_set_context_updates_timestamp(self):
        """Should update updated_at when setting context."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")
        original_updated = segment.updated_at

        segment.set_context(before="Previous")

        assert segment.updated_at > original_updated

    def test_set_notes(self):
        """Should set translation notes."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")

        segment.set_notes("Needs review")

        assert segment.notes == "Needs review"

    def test_word_counts(self):
        """Should calculate word counts correctly."""
        segment = Segment(
            job_id=1,
            segment_number=1,
            source_text="Hello world test",
            target_text="Hola mundo prueba",
        )

        assert segment.word_count_source == 3
        assert segment.word_count_target == 3

    def test_word_count_empty_source(self):
        """Should return 0 for empty source."""
        segment = Segment(job_id=1, segment_number=1, source_text="")

        assert segment.word_count_source == 0

    def test_word_count_none_target(self):
        """Should return 0 for None target."""
        segment = Segment(job_id=1, segment_number=1, source_text="Hello")

        assert segment.word_count_target == 0

    def test_update_source_text(self):
        """Should update source text."""
        segment = Segment(job_id=1, segment_number=1, source_text="Old text")
        original_updated = segment.updated_at

        segment.update_source_text("New source text")

        assert segment.source_text == "New source text"
        assert segment.updated_at > original_updated

    def test_update_source_text_empty_raises(self):
        """Should raise when updating to empty source text."""
        segment = Segment(job_id=1, segment_number=1, source_text="Original")

        with pytest.raises(DomainError, match="Source text cannot be empty"):
            segment.update_source_text("")

    def test_segment_equality(self):
        """Segments with same job_id and segment_number should be equal."""
        seg1 = Segment(job_id=1, segment_number=1, source_text="Text 1")
        seg2 = Segment(job_id=1, segment_number=1, source_text="Text 2")
        seg3 = Segment(job_id=1, segment_number=2, source_text="Text 1")

        assert seg1 == seg2  # Same job_id and segment_number
        assert seg1 != seg3  # Different segment_number