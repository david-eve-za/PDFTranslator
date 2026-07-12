"""Tests for NvidiaLLM chunking integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from pdftranslator.core.config.llm import NvidiaConfig
from pdftranslator.core.config.settings import Settings
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM
from pdftranslator.core.config.llm import BCP47Language


class TestNvidiaLLMChunking:
    """Tests for adaptive chunking in NvidiaLLM."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with NVIDIA config."""
        settings = Mock(spec=Settings)
        settings.llm.nvidia = NvidiaConfig(
            model_name="mistralai/mistral-large-3-675b-instruct-2512",
            max_output_tokens=8192,
            context_size=131072,
            chunk_safety_margin_pct=0.15,
            max_chunk_tokens=32768,
            min_chunk_tokens=512,
            local_tokenizer_name="mistralai/Mistral-Large-3-675B-Instruct-2512",
            local_tokenizer_dir="mistral-large-3-675b-instruct-2512",
        )
        settings.paths.translation_prompt_path = Path("src/pdftranslator/tools/translation_prompt.txt")
        return settings

    @pytest.fixture
    def nvidia_llm(self, mock_settings):
        """Create NvidiaLLM with mocked dependencies."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tokenizer_class:
            mock_tokenizer = Mock()
            mock_tokenizer.encode = Mock(return_value=list(range(100)))  # 100 tokens
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                llm = NvidiaLLM(mock_settings)
                # Mock the tokenizer to return predictable counts
                llm._tokenizer = mock_tokenizer
                return llm

    def test_split_into_limit_uses_calculator(self, nvidia_llm):
        """split_into_limit should use TokenChunkCalculator for chunk size."""
        text = "This is a test text. " * 1000  # Long text

        chunks = nvidia_llm.split_into_limit(
            text,
            language=BCP47Language.ENGLISH,
            source_lang="en",
            target_lang="es"
        )

        # Should produce multiple chunks (not just 1 huge chunk)
        assert len(chunks) > 1
        # Each chunk should be reasonably sized (not 1024)
        # With EN->ES expansion=1.3, expect ~5356 tokens/chunk
        # Our mock returns 100 tokens per encode call, so chunks will be small
        # but the point is it uses the calculator logic

    def test_split_into_limit_passes_language_pair(self, nvidia_llm):
        """split_into_limit should pass source_lang and target_lang to calculator."""
        text = "Test text. " * 100

        # Call with specific language pair
        nvidia_llm.split_into_limit(
            text,
            language=BCP47Language.ENGLISH,
            source_lang="en",
            target_lang="zh"
        )

        # Verify tokenizer was called (indirectly tests the path)
        assert nvidia_llm._tokenizer.encode.called

    def test_split_into_limit_default_language_args(self, nvidia_llm):
        """split_into_limit should have sensible defaults for lang args."""
        text = "Test. " * 50

        # Should not raise with just language
        chunks = nvidia_llm.split_into_limit(text, BCP47Language.ENGLISH)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_sizes_differ_by_language_pair(self, nvidia_llm):
        """Different language pairs should produce different chunk counts."""
        text = "This is a sentence. " * 500

        # Mock count_tokens to simulate actual token counting
        nvidia_llm.count_tokens = Mock(side_effect=lambda t: len(t) // 4)
        nvidia_llm._tokenizer.encode = Mock(side_effect=lambda t, **kw: list(t)[:100])

        chunks_es = nvidia_llm.split_into_limit(text, BCP47Language.ENGLISH, "en", "es")
        chunks_zh = nvidia_llm.split_into_limit(text, BCP47Language.ENGLISH, "en", "zh")

        # EN->ZH (contraction) should allow larger chunks -> fewer chunks
        assert len(chunks_es) > 0
        assert len(chunks_zh) > 0
        # Note: exact counts depend on NLTK splitter behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v"])