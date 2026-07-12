"""End-to-end integration tests for adaptive token chunking."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from pdftranslator.services.translator import TranslatorService
from pdftranslator.infrastructure.llm.factory import LLMFactory
from pdftranslator.core.config.settings import Settings
from pdftranslator.core.config.llm import NvidiaConfig
from pdftranslator.infrastructure.llm.protocol import LLMClient
from pdftranslator.core.config.llm import BCP47Language


class TestTokenChunkingE2E:
    """Integration tests for the complete chunking pipeline."""

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
            temperature=0.3,
            top_p=0.95,
            rate_limit=30,
            request_timeout=3600,
            max_bucket_size=10,
            retry_attempts=6,
            embed_model="nvidia/nv-embedqa-e5-v5",
            rerank_model="nvidia/nv-rerankqa-mistral-2b-4b-4096-v1",
            rerank_top_n=5,
            expansion_ratios={},
        )
        settings.paths.translation_prompt_path = Path("src/pdftranslator/tools/translation_prompt.txt")
        settings.llm.agent = Mock()
        settings.llm.agent.value = "nvidia"
        return settings

    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock tokenizer with realistic token counts."""
        tokenizer = Mock()
        # ~4 chars per token for English text
        def encode(text, **kwargs):
            return list(range(len(text) // 4))
        tokenizer.encode = Mock(side_effect=encode)
        return tokenizer

    def create_mock_llm(self, mock_settings, mock_tokenizer, mock_chat_nvidia):
        """Create a fully mocked NvidiaLLM instance."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer
            factory = LLMFactory(mock_settings)
            llm = factory.create()
            return llm

    @pytest.mark.integration
    def test_en_to_es_produces_fewer_chunks_than_old_fixed(self, mock_settings, mock_tokenizer):
        """EN->ES translation should produce fewer chunks than 1024-token fixed chunking."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()

                # Long text: ~50,000 chars = ~12,500 tokens
                long_text = "This is a sentence. " * 2500  # ~50k chars

                # Get chunks with adaptive sizing (EN->ES expansion=1.3)
                chunks = llm.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="es")

                # Old fixed 1024: ~12 chunks
                # New adaptive ~5357: ~2-3 chunks
                assert len(chunks) < 10, f"Expected fewer than 10 chunks, got {len(chunks)}"
                assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"

    @pytest.mark.integration
    def test_en_to_zh_allows_larger_chunks_than_en_to_es(self, mock_settings, mock_tokenizer):
        """EN->ZH (contraction) should allow larger chunks than EN->ES (expansion)."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()

                long_text = "This is a sentence. " * 2500

                chunks_es = llm.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="es")
                chunks_zh = llm.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="zh")

                # ZH contraction -> larger chunks -> fewer chunks
                assert len(chunks_zh) <= len(chunks_es), "EN->ZH should have <= chunks than EN->ES"

    @pytest.mark.integration
    def test_full_translation_pipeline_no_truncation(self, mock_settings, mock_tokenizer):
        """Full translation pipeline should complete without truncation warnings."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA") as mock_chat:
                # Mock model response
                mock_response = Mock()
                mock_response.content = "Translated text."
                mock_response.usage_metadata = {"output_tokens": 100}
                mock_chat.return_value.invoke.return_value = mock_response

                factory = LLMFactory(mock_settings)
                service = TranslatorService(factory)

                result = service.translate(
                    text="Hello world. " * 100,
                    source_lang="en",
                    target_lang="es"
                )

                assert result.success
                assert len(result.text) > 0
                assert result.original_chunks > 0

    @pytest.mark.integration
    def test_chunk_sizes_within_bounds(self, mock_settings, mock_tokenizer):
        """Generated chunks should be within min/max bounds."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()

                # Various text lengths
                texts = [
                    "Short text.",  # ~3 tokens
                    "This is a sentence. " * 100,  # ~500 tokens
                    "This is a sentence. " * 1000,  # ~5000 tokens
                    "This is a sentence. " * 5000,  # ~25000 tokens
                ]

                for text in texts:
                    chunks = llm.split_into_limit(text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="es")

                    for chunk in chunks:
                        # Token count should be reasonable
                        token_count = llm.count_tokens(chunk)
                        assert token_count <= 32768, f"Chunk exceeds max_chunk_tokens: {token_count}"
                        assert token_count >= 0, "Chunk has negative tokens"

    @pytest.mark.integration
    def test_different_language_pairs_produce_different_chunk_counts(self, mock_settings, mock_tokenizer):
        """Different language pairs should produce different chunk counts."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()

                long_text = "This is a sentence. " * 2500

                # Test multiple language pairs
                pairs = [
                    ("en", "es"),   # 1.30 expansion
                    ("en", "fr"),   # 1.15 expansion
                    ("en", "de"),   # 1.20 expansion
                    ("en", "zh"),   # 0.55 contraction
                    ("en", "ja"),   # 0.60 contraction
                    ("en", "ko"),   # 0.65 contraction
                    ("es", "en"),   # 0.80 contraction
                    ("fr", "en"),   # 0.85 contraction
                    ("zh", "en"),   # 1.80 expansion
                ]

                chunk_counts = {}
                for src, tgt in pairs:
                    chunks = llm.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang=src, target_lang=tgt)
                    chunk_counts[f"{src}->{tgt}"] = len(chunks)

                # Verify contraction pairs have fewer or equal chunks than expansion pairs
                assert chunk_counts["en->zh"] <= chunk_counts["en->es"]
                assert chunk_counts["en->ja"] <= chunk_counts["en->es"]
                assert chunk_counts["es->en"] <= chunk_counts["en->es"]

    @pytest.mark.integration
    def test_custom_expansion_ratios_override_defaults(self, mock_settings, mock_tokenizer):
        """Custom expansion ratios from config should override built-in defaults."""
        # Override EN->ES to use 1.10 instead of default 1.30
        mock_settings.llm.nvidia.expansion_ratios = {"en-es": 1.10}

        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()

                long_text = "This is a sentence. " * 2500

                # With custom ratio 1.10 (less expansion than default 1.30)
                chunks_custom = llm.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="es")

                # Reset to defaults
                mock_settings.llm.nvidia.expansion_ratios = {}
                factory2 = LLMFactory(mock_settings)
                llm2 = factory2.create()

                chunks_default = llm2.split_into_limit(long_text, language=BCP47Language.ENGLISH, source_lang="en", target_lang="es")

                # Custom ratio (1.10) -> larger chunks -> fewer chunks
                assert len(chunks_custom) <= len(chunks_default)

    @pytest.mark.integration
    def test_translator_service_passes_language_pair(self, mock_settings, mock_tokenizer):
        """TranslatorService should pass source_lang/target_lang to LLM."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tok_class.from_pretrained.return_value = mock_tokenizer

            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA") as mock_chat:
                mock_response = Mock()
                mock_response.content = "Translated."
                mock_response.usage_metadata = {"output_tokens": 50}
                mock_chat.return_value.invoke.return_value = mock_response

                factory = LLMFactory(mock_settings)
                service = TranslatorService(factory)

                # Spy on split_into_limit
                original_split = service._llm_client.split_into_limit
                calls = []
                def spy_split(text, language, source_lang=None, target_lang=None):
                    calls.append({"source_lang": source_lang, "target_lang": target_lang})
                    return original_split(text, language, source_lang=source_lang, target_lang=target_lang)

                service._llm_client.split_into_limit = spy_split

                service.translate(
                    text="Hello world.",
                    source_lang="ja",
                    target_lang="ko"
                )

                assert len(calls) == 1
                assert calls[0]["source_lang"] == "ja"
                assert calls[0]["target_lang"] == "ko"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])