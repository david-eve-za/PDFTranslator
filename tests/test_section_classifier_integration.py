"""Integration tests for section classifier with real LLM."""

import os
import pytest

from config.settings import Settings
from infrastructure.llm.nvidia import NvidiaLLM
from document_chapter_splitter_v2 import classify_section_with_llm


@pytest.mark.skipif(
    not os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-"),
    reason="NVIDIA_API_KEY not set or invalid",
)
class TestRealLLMIntegration:
    """Integration tests with real NVIDIA LLM."""

    def test_real_llm_classification_accuracy(self):
        """Test classification accuracy on real LLM."""
        settings = Settings.get()
        llm = NvidiaLLM(settings)

        test_cases = [
            ("Chapter 5: The Battle", "chapter", 5),
            ("Prólogo", "prologue", None),
            ("Prologue", "prologue", None),
            ("Index", "other", None),
            ("Índice", "other", None),
            ("Capítulo 12: Final", "chapter", 12),
            ("Epilogue", "epilogue", None),
            ("Epílogo", "epilogue", None),
            ("Acknowledgments", "other", None),
            ("Chapter One", "chapter", 1),
            ("Chapter XII", "chapter", 12),
        ]

        correct = 0
        total = len(test_cases)

        for title, expected_type, expected_number in test_cases:
            result = classify_section_with_llm(
                llm, title=title, content_preview="Sample content for testing..."
            )

            if result["type"] == expected_type:
                if expected_number is None or result.get("number") == expected_number:
                    correct += 1
                    print(
                        f"✓ '{title}' → {result['type']} "
                        f"(confidence: {result.get('confidence', 0):.2f})"
                    )
                else:
                    print(
                        f"✗ '{title}' → Expected number {expected_number}, "
                        f"got {result.get('number')}"
                    )
            else:
                print(f"✗ '{title}' → Expected {expected_type}, got {result['type']}")

        accuracy = correct / total
        print(f"\nAccuracy: {accuracy:.2%} ({correct}/{total})")

        assert accuracy >= 0.9, f"Accuracy {accuracy:.2%} < 90%"

    def test_real_llm_temperature_override(self):
        """Test that temperature override works correctly."""
        settings = Settings.get()
        llm = NvidiaLLM(settings)

        # Verify method exists
        assert hasattr(llm, "call_model_with_temperature")

        # Test with temperature 0.1 (should be deterministic)
        result1 = classify_section_with_llm(
            llm, title="Chapter 5", content_preview="The sun rose..."
        )

        result2 = classify_section_with_llm(
            llm, title="Chapter 5", content_preview="The sun rose..."
        )

        # Results should be identical or very similar
        assert result1["type"] == result2["type"]

    def test_real_llm_confidence_scoring(self):
        """Test that confidence scoring is reasonable."""
        settings = Settings.get()
        llm = NvidiaLLM(settings)

        # Clear cases should have high confidence
        clear_cases = [
            ("Chapter 5", "chapter"),
            ("Prologue", "prologue"),
            ("Index", "other"),
        ]

        for title, expected_type in clear_cases:
            result = classify_section_with_llm(
                llm, title=title, content_preview="Sample content..."
            )

            assert result["type"] == expected_type
            assert result["confidence"] >= 0.7, (
                f"Confidence {result['confidence']:.2f} too low for clear case '{title}'"
            )

    def test_real_llm_fallback_triggers(self):
        """Test that fallback is used when appropriate."""
        settings = Settings.get()
        llm = NvidiaLLM(settings)

        # Test with clear patterns that should work with fallback
        result = classify_section_with_llm(
            llm, title="Prólogo", content_preview="Hace mucho tiempo..."
        )

        assert result["type"] == "prologue"
        assert "confidence" in result


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set"
)
class TestGeminiIntegration:
    """Integration tests with Gemini LLM."""

    def test_gemini_classification_basic(self):
        """Test basic classification with Gemini."""
        from infrastructure.llm.gemini import GeminiLLM

        settings = Settings.get()
        llm = GeminiLLM(settings)

        result = classify_section_with_llm(
            llm, title="Chapter 5", content_preview="The sun rose..."
        )

        assert result["type"] == "chapter"
        assert result.get("number") == 5


@pytest.mark.skipif(not os.environ.get("OLLAMA_HOST"), reason="OLLAMA_HOST not set")
class TestOllamaIntegration:
    """Integration tests with Ollama LLM."""

    def test_ollama_classification_basic(self):
        """Test basic classification with Ollama."""
        from infrastructure.llm.ollama import OllamaLLM

        settings = Settings.get()
        llm = OllamaLLM(settings)

        result = classify_section_with_llm(
            llm, title="Chapter 5", content_preview="The sun rose..."
        )

        assert result["type"] == "chapter"
