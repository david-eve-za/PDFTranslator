"""Tests for GlossaryBuildProgress model."""

import pytest
from datetime import datetime

from pdftranslator.database.models import GlossaryBuildProgress


def test_glossary_build_progress_creation():
    """Test creating a progress record."""
    progress = GlossaryBuildProgress(
        work_id=1,
        volume_id=2,
        entity_text="Harry Potter",
        phase="extracted",
        entity_type="character",
        frequency=10,
    )
    assert progress.work_id == 1
    assert progress.volume_id == 2
    assert progress.entity_text == "Harry Potter"
    assert progress.phase == "extracted"
    assert progress.is_complete() is False


def test_glossary_build_progress_is_complete():
    """Test is_complete method."""
    progress = GlossaryBuildProgress(phase="saved")
    assert progress.is_complete() is True

    progress.phase = "extracted"
    assert progress.is_complete() is False


def test_glossary_build_progress_next_phase():
    """Test next_phase method."""
    progress = GlossaryBuildProgress(phase="extracted")
    assert progress.next_phase() == "validated"

    progress.phase = "validated"
    assert progress.next_phase() == "translated"

    progress.phase = "translated"
    assert progress.next_phase() == "saved"

    progress.phase = "saved"
    assert progress.next_phase() is None


def test_glossary_build_progress_default_values():
    """Test default values."""
    progress = GlossaryBuildProgress()
    assert progress.frequency == 1
    assert progress.phase == "extracted"
    assert progress.contexts == []
    assert progress.embedding is None
    assert progress.translation is None
