"""
Unit tests for TranslationJob domain model.

CUPID Principle: Predictable
- Tests domain invariants
- Tests business behavior
- No infrastructure dependencies
"""

from __future__ import annotations
import pytest
from datetime import datetime

from src.pdftranslator.services.translation.domain.models.job import TranslationJob, JobStatus, JobPriority
from src.pdftranslator.services.translation.domain.models.glossary_ref import GlossaryReference
from src.pdftranslator.services.translation.domain.repositories.exceptions import DomainError


class TestTranslationJobModel:
    """Tests for TranslationJob aggregate root."""

    def test_create_valid_job(self):
        """Should create job with valid data."""
        job = TranslationJob(
            source_lang="en",
            target_lang="es",
            work_id=1,
            source_text="Hello world",
            priority=JobPriority.NORMAL,
            llm_provider="openai",
            model_name="gpt-4",
        )

        assert job.source_lang == "en"
        assert job.target_lang == "es"
        assert job.work_id == 1
        assert job.source_text == "Hello world"
        assert job.priority == JobPriority.NORMAL
        assert job.llm_provider == "openai"
        assert job.model_name == "gpt-4"
        assert job.status == JobStatus.PENDING
        assert job.uuid is not None
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_create_job_same_lang_raises(self):
        """Should raise DomainError when source equals target."""
        with pytest.raises(DomainError, match="must differ"):
            TranslationJob(source_lang="en", target_lang="en", work_id=1)

    def test_create_job_invalid_source_lang_raises(self):
        """Should raise for invalid source language code."""
        with pytest.raises(DomainError, match="ISO 639-1"):
            TranslationJob(source_lang="eng", target_lang="es", work_id=1)

    def test_create_job_invalid_target_lang_raises(self):
        """Should raise for invalid target language code."""
        with pytest.raises(DomainError, match="ISO 639-1"):
            TranslationJob(source_lang="en", target_lang="spa", work_id=1)

    def test_queue_from_pending(self):
        """Should transition from PENDING to QUEUED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        assert job.status == JobStatus.PENDING

        job.queue()

        assert job.status == JobStatus.QUEUED

    def test_queue_from_wrong_status_raises(self):
        """Should raise when queuing from non-PENDING status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()  # Now QUEUED

        with pytest.raises(DomainError, match="Cannot queue job from status"):
            job.queue()

    def test_start_from_queued(self):
        """Should transition from QUEUED to IN_PROGRESS."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        assert job.status == JobStatus.QUEUED

        job.start("openai", "gpt-4")

        assert job.status == JobStatus.IN_PROGRESS
        assert job.llm_provider == "openai"
        assert job.model_name == "gpt-4"
        assert job.started_at is not None

    def test_start_from_wrong_status_raises(self):
        """Should raise when starting from non-QUEUED status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        # Goes PENDING -> COMPLETED (skip QUEUED)
        job.queue()
        job.complete("translated")

        with pytest.raises(DomainError, match="Cannot start job from status"):
            job.start("openai", "gpt-4")

    def test_complete_from_in_progress(self):
        """Should transition from IN_PROGRESS to COMPLETED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")

        job.complete("Translation complete")

        assert job.status == JobStatus.COMPLETED
        assert job.target_text == "Translation complete"
        assert job.completed_at is not None
        assert job.progress == 100.0

    def test_complete_from_wrong_status_raises(self):
        """Should raise when completing from non-IN_PROGRESS status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()

        with pytest.raises(DomainError, match="Cannot complete job from status"):
            job.complete("text")

    def test_fail_from_queued(self):
        """Should transition from QUEUED to FAILED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()

        job.fail("API error")

        assert job.status == JobStatus.FAILED
        assert job.error_message == "API error"
        assert job.completed_at is not None

    def test_fail_from_in_progress(self):
        """Should transition from IN_PROGRESS to FAILED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")

        job.fail("Timeout")

        assert job.status == JobStatus.FAILED
        assert job.error_message == "Timeout"

    def test_fail_from_completed_raises(self):
        """Should raise when failing from COMPLETED status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")
        job.complete("done")

        with pytest.raises(DomainError, match="Cannot fail job from status"):
            job.fail("error")

    def test_pause_from_in_progress(self):
        """Should transition from IN_PROGRESS to PAUSED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")

        job.pause()

        assert job.status == JobStatus.PAUSED

    def test_pause_from_wrong_status_raises(self):
        """Should raise when pausing from non-IN_PROGRESS status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()

        with pytest.raises(DomainError, match="Cannot pause job from status"):
            job.pause()

    def test_resume_from_paused(self):
        """Should transition from PAUSED to IN_PROGRESS."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")
        job.pause()

        job.resume()

        assert job.status == JobStatus.IN_PROGRESS

    def test_resume_from_wrong_status_raises(self):
        """Should raise when resuming from non-PAUSED status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()

        with pytest.raises(DomainError, match="Cannot resume job from status"):
            job.resume()

    def test_cancel_from_pending(self):
        """Should transition from PENDING to CANCELLED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)

        job.cancel()

        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None

    def test_cancel_from_queued(self):
        """Should transition from QUEUED to CANCELLED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()

        job.cancel()

        assert job.status == JobStatus.CANCELLED

    def test_cancel_from_in_progress(self):
        """Should transition from IN_PROGRESS to CANCELLED."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")

        job.cancel()

        assert job.status == JobStatus.CANCELLED

    def test_cancel_from_completed_raises(self):
        """Should raise when cancelling from COMPLETED status."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.queue()
        job.start("openai", "gpt-4")
        job.complete("done")

        with pytest.raises(DomainError, match="Cannot cancel job from status"):
            job.cancel()

    def test_update_priority(self):
        """Should update job priority."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        original_updated = job.updated_at

        job.update_priority(JobPriority.HIGH)

        assert job.priority == JobPriority.HIGH
        assert job.updated_at > original_updated

    def test_add_glossary_ref(self):
        """Should add glossary reference."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        ref = GlossaryReference(
            glossary_id=1,
            name="Test Glossary",
            source_lang="en",
            target_lang="es",
            priority=10,
            entry_count=100,
        )

        job.add_glossary_ref(ref)

        assert len(job.glossary_refs) == 1
        assert job.glossary_refs[0] == ref

    def test_add_duplicate_glossary_ref_raises(self):
        """Should raise when adding duplicate glossary reference."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        ref = GlossaryReference(
            glossary_id=1,
            name="Test",
            source_lang="en",
            target_lang="es",
        )
        job.add_glossary_ref(ref)

        with pytest.raises(DomainError, match="already added"):
            job.add_glossary_ref(ref)

    def test_remove_glossary_ref(self):
        """Should remove glossary reference."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        ref = GlossaryReference(
            glossary_id=1,
            name="Test",
            source_lang="en",
            target_lang="es",
        )
        job.add_glossary_ref(ref)

        result = job.remove_glossary_ref(1)

        assert result is True
        assert len(job.glossary_refs) == 0

    def test_remove_missing_glossary_ref(self):
        """Should return False for missing glossary reference."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)

        result = job.remove_glossary_ref(999)

        assert result is False

    def test_segment_management(self):
        """Should manage segments through aggregate."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        segment = job.create_segment(1, "Hello world")

        assert job.segment_count == 1
        assert segment.segment_number == 1
        assert segment.source_text == "Hello world"
        assert job.get_segment(1) == segment

    def test_duplicate_segment_number_raises(self):
        """Should raise when creating duplicate segment number."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        job.create_segment(1, "First")

        with pytest.raises(DomainError, match="already exists"):
            job.create_segment(1, "Duplicate")

    def test_translation_progress_calculation(self):
        """Should calculate translation progress correctly."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)

        seg1 = job.create_segment(1, "Hello world this is a test")
        seg2 = job.create_segment(2, "Another sentence")
        seg3 = job.create_segment(3, "Third one")

        assert job.segment_count == 3
        assert job.translated_segment_count == 0
        assert job.progress == 0.0

        seg1.set_translation("Hola mundo esta es una prueba")
        job._recalculate_progress()

        assert job.translated_segment_count == 1
        assert job.progress == pytest.approx(33.33, rel=0.1)

        seg2.set_translation("Otra oración")
        job._recalculate_progress()

        assert job.translated_segment_count == 2
        assert job.progress == pytest.approx(66.67, rel=0.1)

        seg3.set_translation("Tercero")
        job._recalculate_progress()

        assert job.translated_segment_count == 3
        assert job.progress == 100.0

    def test_word_count_calculation(self):
        """Should calculate word counts correctly."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)
        seg1 = job.create_segment(1, "This is five words here")
        seg1.set_translation("Esto son cinco palabras aca")
        seg2 = job.create_segment(2, "Two words")
        job._recalculate_progress()

        assert job.word_count_source == 7  # 5 + 2
        assert job.word_count_target == 5  # 5 + 0 (seg2 not translated)

    def test_calculate_progress_empty_job(self):
        """Should return 0 progress for job with no segments."""
        job = TranslationJob(source_lang="en", target_lang="es", work_id=1)

        assert job.progress == 0.0
        assert job.segment_count == 0
        assert job.translated_segment_count == 0


class TestJobPriority:
    """Tests for JobPriority enum."""

    def test_priority_values(self):
        """Should have correct priority values."""
        assert JobPriority.LOW.value == 10
        assert JobPriority.NORMAL.value == 50
        assert JobPriority.HIGH.value == 90

    def test_priority_ordering(self):
        """Should support ordering by value."""
        assert JobPriority.LOW < JobPriority.NORMAL
        assert JobPriority.NORMAL < JobPriority.HIGH


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_status_values(self):
        """Should have expected status values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.IN_PROGRESS.value == "in_progress"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.PAUSED.value == "paused"
        assert JobStatus.CANCELLED.value == "cancelled"