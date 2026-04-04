# tests/test_document_chapter_splitter_v2.py
"""Tests for document_chapter_splitter_v2 with Docling."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from document_chapter_splitter_v2 import (
    SectionClassifier,
    classify_section_with_llm,
)


SECTION_CLASSIFICATION_PROMPT = """
Eres un clasificador de secciones de libros narrativos.

Tu tarea es clasificar una sección como:
- "prologue": Prólogo o prefacio del autor
- "chapter": Capítulo numerado o titulado
- "epilogue": Epílogo o postfacio
- "other": Índice, agradecimientos, derechos, publicidad, etc.

INPUT:
Título: {title}
Primeras 300 caracteres del contenido:
{content_preview}

Responde SOLO con JSON válido:
{{"type": "prologue"|"chapter"|"epilogue"|"other", "number": <int|null>}}

Ejemplos:
Input: "Capítulo 5: La batalla" → {{"type": "chapter", "number": 5}}
Input: "Prólogo" → {{"type": "prologue", "number": null}}
Input: "Índice" → {{"type": "other", "number": null}}
"""


def test_section_classifier_initializes():
    """Test SectionClassifier initializes."""
    mock_llm = MagicMock()
    classifier = SectionClassifier(mock_llm)

    assert classifier.llm is not None


def test_classify_section_with_llm_returns_valid_json():
    """Test classify_section_with_llm returns valid JSON."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = '{"type": "chapter", "number": 5}'

    result = classify_section_with_llm(
        mock_llm,
        title="Chapter 5: The Battle",
        content_preview="The sun rose over the mountains...",
    )

    assert result["type"] == "chapter"
    assert result["number"] == 5


def test_classify_section_with_llm_handles_prologue():
    """Test classify_section_with_llm handles prologue."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = '{"type": "prologue", "number": null}'

    result = classify_section_with_llm(
        mock_llm, title="Prólogo", content_preview="Hace mucho tiempo..."
    )

    assert result["type"] == "prologue"
    assert result["number"] is None


def test_classify_section_with_llm_handles_other():
    """Test classify_section_with_llm handles non-narrative sections."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = '{"type": "other", "number": null}'

    result = classify_section_with_llm(
        mock_llm, title="Índice", content_preview="Capítulo 1..........1"
    )

    assert result["type"] == "other"


def test_classify_section_with_llm_cleans_json():
    """Test classify_section_with_llm cleans markdown fences."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = """```json
{"type": "chapter", "number": 1}
```"""

    result = classify_section_with_llm(
        mock_llm, title="Chapter 1", content_preview="Text..."
    )

    assert result["type"] == "chapter"
    assert result["number"] == 1


def test_classify_section_with_llm_handles_invalid_json():
    """Test classify_section_with_llm handles invalid JSON."""
    mock_llm = MagicMock()
    mock_llm.call_model.return_value = "invalid json"

    with pytest.raises(ValueError):
        classify_section_with_llm(
            mock_llm, title="Chapter 1", content_preview="Text..."
        )
