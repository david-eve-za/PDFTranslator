"""Tests for enhanced section classifier with fallback and confidence."""

import pytest
from unittest.mock import MagicMock

from document_chapter_splitter_v2 import (
    classify_section_with_llm,
    _fallback_classification,
    _roman_to_int,
    SectionClassifier,
)


class TestRomanToInt:
    """Test Roman numeral conversion."""

    def test_basic_numerals(self):
        """Test basic Roman numerals."""
        assert _roman_to_int("I") == 1
        assert _roman_to_int("V") == 5
        assert _roman_to_int("X") == 10
        assert _roman_to_int("L") == 50
        assert _roman_to_int("C") == 100
        assert _roman_to_int("D") == 500
        assert _roman_to_int("M") == 1000

    def test_complex_numerals(self):
        """Test complex Roman numerals."""
        assert _roman_to_int("IV") == 4
        assert _roman_to_int("IX") == 9
        assert _roman_to_int("XII") == 12
        assert _roman_to_int("XIV") == 14
        assert _roman_to_int("XIX") == 19
        assert _roman_to_int("XX") == 20
        assert _roman_to_int("XL") == 40
        assert _roman_to_int("XC") == 90
        assert _roman_to_int("CD") == 400
        assert _roman_to_int("CM") == 900

    def test_case_insensitive(self):
        """Test that conversion is case-insensitive."""
        assert _roman_to_int("xii") == 12
        assert _roman_to_int("Xii") == 12
        assert _roman_to_int("xII") == 12

    def test_invalid_character_raises(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid Roman numeral character"):
            _roman_to_int("ABC")


class TestFallbackClassification:
    """Test rule-based fallback classification."""

    def test_prologue_patterns(self):
        """Test prologue pattern matching."""
        result = _fallback_classification("Prólogo", "Content...")
        assert result["type"] == "prologue"
        assert result["number"] is None
        assert result["confidence"] >= 0.9

        result = _fallback_classification("Prologue", "Content...")
        assert result["type"] == "prologue"
        assert result["confidence"] >= 0.9

        result = _fallback_classification("Preface", "Content...")
        assert result["type"] == "prologue"

    def test_epilogue_patterns(self):
        """Test epilogue pattern matching."""
        result = _fallback_classification("Epílogo", "Content...")
        assert result["type"] == "epilogue"
        assert result["number"] is None
        assert result["confidence"] >= 0.9

        result = _fallback_classification("Epilogue", "Content...")
        assert result["type"] == "epilogue"
        assert result["confidence"] >= 0.9

        result = _fallback_classification("Afterword", "Content...")
        assert result["type"] == "epilogue"

    def test_other_patterns(self):
        """Test non-narrative pattern matching."""
        result = _fallback_classification("Index", "Content...")
        assert result["type"] == "other"
        assert result["number"] is None
        assert result["confidence"] >= 0.9

        result = _fallback_classification("Índice", "Content...")
        assert result["type"] == "other"

        result = _fallback_classification("Acknowledgments", "Content...")
        assert result["type"] == "other"

        result = _fallback_classification("Table of Contents", "Content...")
        assert result["type"] == "other"

    def test_chapter_with_arabic_numerals(self):
        """Test chapter extraction with Arabic numerals."""
        result = _fallback_classification("Chapter 5: The Battle", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 5
        assert result["confidence"] >= 0.85

        result = _fallback_classification("Capítulo 12", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 12

        result = _fallback_classification("Chap. 7", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 7

    def test_chapter_with_roman_numerals(self):
        """Test chapter extraction with Roman numerals."""
        result = _fallback_classification("Chapter XII", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 12
        assert result["confidence"] >= 0.85

        result = _fallback_classification("Capítulo IV", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 4

    def test_uncertain_defaults_to_chapter(self):
        """Test that uncertain titles default to chapter."""
        result = _fallback_classification("The Beginning", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] is None
        assert result["confidence"] < 0.5  # Low confidence for uncertain

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        result = _fallback_classification("PROLOGUE", "Content...")
        assert result["type"] == "prologue"

        result = _fallback_classification("CHAPTER 5", "Content...")
        assert result["type"] == "chapter"
        assert result["number"] == 5


class TestClassifySectionWithLLM:
    """Test LLM-based classification with confidence."""

    def test_classify_with_high_confidence(self):
        """Test that high confidence results are accepted."""
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
        mock_llm.call_model_with_temperature.assert_called_once()

    def test_classify_with_moderate_confidence_logs_warning(self):
        """Test that moderate confidence logs warning but accepts."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.return_value = (
            '{"type": "chapter", "number": 5, "confidence": 0.6}'
        )

        result = classify_section_with_llm(
            mock_llm, title="Chapter 5", content_preview="Content..."
        )

        assert result["type"] == "chapter"
        assert result["confidence"] == 0.6

    def test_classify_with_low_confidence_uses_fallback(self):
        """Test that low confidence triggers fallback."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.return_value = (
            '{"type": "chapter", "number": 5, "confidence": 0.3}'
        )

        result = classify_section_with_llm(
            mock_llm, title="Chapter 5: The Battle", content_preview="Content..."
        )

        # Fallback should be used
        assert result["type"] == "chapter"
        assert result["number"] == 5
        assert result["confidence"] >= 0.85  # Fallback confidence

    def test_classify_invalid_json_uses_fallback(self):
        """Test that invalid JSON triggers fallback."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.return_value = "invalid json"

        result = classify_section_with_llm(
            mock_llm, title="Chapter 5", content_preview="Content..."
        )

        # Should use fallback
        assert result["type"] == "chapter"
        assert result["number"] == 5

    def test_classify_llm_error_uses_fallback(self):
        """Test that LLM errors trigger fallback."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.side_effect = Exception("API error")

        result = classify_section_with_llm(
            mock_llm, title="Chapter 5", content_preview="Content..."
        )

        # Should use fallback
        assert result["type"] == "chapter"

    def test_classify_without_temperature_override(self):
        """Test fallback to call_model if no temperature override."""
        mock_llm = MagicMock(spec=["call_model", "get_current_model_name"])
        mock_llm.call_model.return_value = (
            '{"type": "chapter", "number": 5, "confidence": 0.95}'
        )

        result = classify_section_with_llm(
            mock_llm, title="Chapter 5", content_preview="Content..."
        )

        assert result["type"] == "chapter"
        mock_llm.call_model.assert_called_once()

    def test_classify_empty_title_returns_other(self):
        """Test that empty title defaults to 'other'."""
        mock_llm = MagicMock()

        result = classify_section_with_llm(
            mock_llm, title="", content_preview="Content..."
        )

        assert result["type"] == "other"
        assert result["confidence"] == 1.0

    def test_classify_empty_content_logs_warning(self):
        """Test that empty content logs warning."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.return_value = (
            '{"type": "chapter", "number": 1, "confidence": 0.9}'
        )

        result = classify_section_with_llm(
            mock_llm, title="Chapter 1", content_preview=""
        )

        assert result["type"] == "chapter"


class TestSectionClassifierEnhanced:
    """Test SectionClassifier class."""

    def test_classifier_uses_enhanced_method(self):
        """Test that classifier integrates with enhanced method."""
        mock_llm = MagicMock()
        mock_llm.call_model_with_temperature.return_value = (
            '{"type": "prologue", "number": null, "confidence": 0.95}'
        )

        classifier = SectionClassifier(mock_llm)
        result = classifier.classify("Prologue", "Once upon a time...")

        assert result["type"] == "prologue"
        assert result["confidence"] >= 0.9
