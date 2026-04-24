# tests/test_document_chapter_splitter_v2.py
"""Tests for document_chapter_splitter_v2 with Docling."""

import pytest
from unittest.mock import MagicMock

from document_chapter_splitter_v2 import (
    SectionClassifier,
    classify_section_with_llm,
    split_document_v2,
)


def test_section_classifier_initializes():
    """Test SectionClassifier initializes."""
    mock_llm = MagicMock()
    classifier = SectionClassifier(mock_llm)

    assert classifier.llm is not None


def test_classify_section_with_llm_returns_valid_json():
    """Test classify_section_with_llm returns valid JSON."""
    mock_llm = MagicMock()
    mock_llm.call_model_with_temperature.return_value = (
        '{"type": "chapter", "number": 5, "confidence": 0.95}'
    )

    result = classify_section_with_llm(
        mock_llm,
        title="Chapter 5: The Battle",
        content_preview="The sun rose over the mountains...",
    )

    assert result["type"] == "chapter"
    assert result["number"] == 5
    assert result["confidence"] >= 0.9


def test_classify_section_with_llm_handles_prologue():
    """Test classify_section_with_llm handles prologue."""
    mock_llm = MagicMock()
    mock_llm.call_model_with_temperature.return_value = (
        '{"type": "prologue", "number": null, "confidence": 0.95}'
    )

    result = classify_section_with_llm(
        mock_llm, title="Prólogo", content_preview="Hace mucho tiempo..."
    )

    assert result["type"] == "prologue"
    assert result["number"] is None


def test_classify_section_with_llm_handles_other():
    """Test classify_section_with_llm handles non-narrative sections."""
    mock_llm = MagicMock()
    mock_llm.call_model_with_temperature.return_value = (
        '{"type": "other", "number": null, "confidence": 0.98}'
    )

    result = classify_section_with_llm(
        mock_llm, title="Índice", content_preview="Capítulo 1..........1"
    )

    assert result["type"] == "other"


def test_classify_section_with_llm_cleans_json():
    """Test classify_section_with_llm cleans markdown fences."""
    mock_llm = MagicMock()
    mock_llm.call_model_with_temperature.return_value = """```json
{"type": "chapter", "number": 1, "confidence": 0.9}
```"""

    result = classify_section_with_llm(
        mock_llm, title="Chapter 1", content_preview="Text..."
    )

    assert result["type"] == "chapter"
    assert result["number"] == 1


def test_classify_section_with_llm_handles_invalid_json():
    """Test classify_section_with_llm handles invalid JSON."""
    mock_llm = MagicMock()
    mock_llm.call_model_with_temperature.return_value = "invalid json"

    # Should use fallback classification
    result = classify_section_with_llm(
        mock_llm, title="Chapter 1", content_preview="Text..."
    )

    # Fallback should classify as chapter
    assert result["type"] == "chapter"


def test_split_document_v2_raises_on_missing_file():
    """Test split_document_v2 raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        split_document_v2("/nonexistent/path/file.pdf")


def test_split_document_v2_accepts_llm_parameter():
    """Test split_document_v2 accepts injected LLM client."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = '{"type": "chapter", "number": 1}'

    classifier = SectionClassifier(mock_llm)
    assert classifier.llm is mock_llm
