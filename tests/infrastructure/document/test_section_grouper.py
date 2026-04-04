"""Tests for SectionGrouper."""

import pytest
from unittest.mock import MagicMock

from docling_core.types.doc import (
    DoclingDocument,
    SectionHeaderItem,
    TextItem,
    TitleItem,
)

from infrastructure.document.section_grouper import SectionGrouper


def _create_mock_document_with_sections():
    """Create a mock DoclingDocument with sections."""
    mock_doc = MagicMock(spec=DoclingDocument)

    # Mock items with hierarchy
    items = [
        (MagicMock(spec=TitleItem, text="Book Title"), 0),
        (MagicMock(spec=TextItem, text="Introduction text..."), 1),
        (MagicMock(spec=SectionHeaderItem, text="Chapter 1", level=1), 1),
        (MagicMock(spec=TextItem, text="Chapter 1 content line 1"), 2),
        (MagicMock(spec=TextItem, text="Chapter 1 content line 2"), 2),
        (MagicMock(spec=SectionHeaderItem, text="Chapter 2", level=1), 1),
        (MagicMock(spec=TextItem, text="Chapter 2 content"), 2),
    ]

    mock_doc.iterate_items.return_value = iter(items)
    return mock_doc


def test_section_grouper_initializes():
    """Test SectionGrouper initializes."""
    grouper = SectionGrouper()
    assert grouper is not None


def test_section_grouper_groups_by_headers():
    """Test SectionGrouper groups content under headers."""
    grouper = SectionGrouper()
    mock_doc = _create_mock_document_with_sections()

    sections = grouper.group_by_sections(mock_doc)

    assert len(sections) >= 2
    assert any("Chapter 1" in s["title"] for s in sections)
    assert any("Chapter 2" in s["title"] for s in sections)


def test_section_grouper_includes_content():
    """Test SectionGrouper includes content for each section."""
    grouper = SectionGrouper()
    mock_doc = _create_mock_document_with_sections()

    sections = grouper.group_by_sections(mock_doc)

    chapter1 = next(s for s in sections if "Chapter 1" in s["title"])
    assert "Chapter 1 content" in chapter1["content"]


def test_section_grouper_tracks_level():
    """Test SectionGrouper tracks hierarchy level."""
    grouper = SectionGrouper()
    mock_doc = _create_mock_document_with_sections()

    sections = grouper.group_by_sections(mock_doc)

    for section in sections:
        assert "level" in section
        assert isinstance(section["level"], int)


def test_section_grouper_handles_empty_document():
    """Test SectionGrouper handles empty document."""
    grouper = SectionGrouper()
    mock_doc = MagicMock(spec=DoclingDocument)
    mock_doc.iterate_items.return_value = iter([])

    sections = grouper.group_by_sections(mock_doc)

    assert sections == []


def test_section_grouper_extracts_text_items():
    """Test SectionGrouper extracts text from TextItems."""
    grouper = SectionGrouper()

    # Create mock with text items only
    mock_doc = MagicMock(spec=DoclingDocument)
    items = [
        (MagicMock(spec=TextItem, text="Paragraph 1"), 0),
        (MagicMock(spec=TextItem, text="Paragraph 2"), 0),
    ]
    mock_doc.iterate_items.return_value = iter(items)

    sections = grouper.group_by_sections(mock_doc)

    assert len(sections) == 1
    assert "Paragraph 1" in sections[0]["content"]
    assert "Paragraph 2" in sections[0]["content"]
