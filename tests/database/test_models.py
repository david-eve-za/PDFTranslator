# tests/database/test_models.py
import pytest
import numpy as np
from database.models import (
    Work,
    Volume,
    Chapter,
    GlossaryEntry,
    TermContext,
    ContextExample,
)


def test_work_creation():
    work = Work(id=1, title="Test Novel", source_lang="en", target_lang="es")
    assert work.id == 1
    assert work.title == "Test Novel"
    assert work.source_lang == "en"
    assert work.target_lang == "es"


def test_work_defaults():
    work = Work(id=None, title="Test")
    assert work.id is None
    assert work.title == "Test"
    assert work.source_lang is None
    assert work.target_lang is None


def test_volume_creation():
    volume = Volume(id=1, work_id=1, volume_number=1, title="Vol 1")
    assert volume.id == 1
    assert volume.work_id == 1
    assert volume.volume_number == 1
    assert volume.title == "Vol 1"


def test_volume_with_embedding():
    """Volume no longer has embedding field - test that it works without it."""
    volume = Volume(id=1, work_id=1, volume_number=1, title="Vol 1")
    assert volume.id == 1
    assert volume.title == "Vol 1"


def test_chapter_creation():
    chapter = Chapter(id=1, volume_id=1, chapter_number=1, title="Chapter 1")
    assert chapter.id == 1
    assert chapter.volume_id == 1
    assert chapter.chapter_number == 1


def test_glossary_entry_creation():
    entry = GlossaryEntry(id=1, work_id=1, source_term="staff", target_term="personal")
    assert entry.id == 1
    assert entry.source_term == "staff"
    assert entry.target_term == "personal"


def test_glossary_entry_proper_noun():
    """GlossaryEntry no longer has is_proper_noun - test notes instead."""
    entry = GlossaryEntry(
        id=1, work_id=1, source_term="Tempest", target_term=None, notes="Proper noun"
    )
    assert entry.notes == "Proper noun"


def test_term_context_creation():
    context = TermContext(
        id=1, term_id=1, context_hint="objeto mágico", translation="baculo"
    )
    assert context.id == 1
    assert context.context_hint == "objeto mágico"
    assert context.translation == "baculo"
    assert context.examples == []


def test_context_example_creation():
    example = ContextExample(
        id=1,
        context_id=1,
        original_sentence="He held his staff",
        translated_sentence="El sostenía su baculo",
    )
    assert example.id == 1
    assert example.original_sentence == "He held his staff"
