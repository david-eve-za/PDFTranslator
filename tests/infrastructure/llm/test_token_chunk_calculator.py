"""Tests for TokenChunkCalculator."""

from unittest.mock import Mock

import pytest

from pdftranslator.core.config.llm import NvidiaConfig
from pdftranslator.infrastructure.llm.protocol import LLMClient
from pdftranslator.infrastructure.llm.token_chunk_calculator import TokenChunkCalculator


class TestTokenChunkCalculator:
    """Tests for adaptive token chunk calculation."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = Mock(spec=LLMClient)
        llm.count_tokens = Mock(return_value=100)
        return llm

    @pytest.fixture
    def config(self):
        """Create test config."""
        return NvidiaConfig(
            max_output_tokens=8192,
            context_size=131072,
            chunk_safety_margin_pct=0.15,
            max_chunk_tokens=32768,
            min_chunk_tokens=512,
        )

    @pytest.fixture
    def calculator(self, mock_llm, config):
        """Create calculator instance."""
        return TokenChunkCalculator(mock_llm, config)

    def test_measure_prompt_tokens_formats_template(self, calculator, mock_llm):
        """Prompt tokens measured with formatted template."""
        template = "Translate {text_chunk} from {source_lang} to {target_lang}"
        tokens = calculator.measure_prompt_tokens(template, "en", "es")

        # Verify template was formatted with sample text
        mock_llm.count_tokens.assert_called_once()
        call_args = mock_llm.count_tokens.call_args[0][0]
        assert "en" in call_args
        assert "es" in call_args
        assert "Sample text" in call_args
        assert tokens == 100

    def test_get_expansion_ratio_known_pair_en_es(self, calculator):
        """EN->ES expansion ratio should be 1.30."""
        ratio = calculator.get_expansion_ratio("en", "es")
        assert ratio == 1.30

    def test_get_expansion_ratio_known_pair_en_zh(self, calculator):
        """EN->ZH expansion ratio should be 0.55."""
        ratio = calculator.get_expansion_ratio("en", "zh")
        assert ratio == 0.55

    def test_get_expansion_ratio_unknown_pair_fallback(self, calculator):
        """Unknown language pair should fallback to 1.15."""
        ratio = calculator.get_expansion_ratio("xx", "yy")
        assert ratio == 1.15

    def test_get_expansion_ratio_custom_override(self, mock_llm, config):
        """Custom expansion ratios from custom_ratios param should override defaults."""
        calculator = TokenChunkCalculator(
            mock_llm, config, custom_ratios={"en-es": 1.25, "en-fr": 1.10}
        )

        assert calculator.get_expansion_ratio("en", "es") == 1.25
        assert calculator.get_expansion_ratio("en", "fr") == 1.10
        # Non-overridden should still use defaults
        assert calculator.get_expansion_ratio("en", "zh") == 0.55

    def test_calculate_chunk_size_en_es_8192_output(self, calculator):
        """EN->ES with 8192 output should yield ~5356 chunk tokens."""
        # Formula: (8192 / 1.30) * 0.85 = 5356.3 -> round = 5356
        # Also check context limit: (131072 - 100 - 8192) * 0.85 = 122780 * 0.85 = 104363
        # min(5356, 104363, 32768) = 5356
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=1.30)
        assert chunk == 5356

    def test_calculate_chunk_size_en_zh_8192_output(self, calculator):
        """EN->ZH with 8192 output should yield ~12660 chunk tokens."""
        # (8192 / 0.55) * 0.85 = 12660.36 -> round = 12660
        # Context: (131072 - 100 - 8192) * 0.85 = 104363
        # min(12660, 104363, 32768) = 12660
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=0.55)
        assert chunk == 12660

    def test_calculate_chunk_size_respects_min_chunk(self, calculator):
        """Result should not go below min_chunk_tokens."""
        # Very high expansion ratio - yields value below min
        # (8192 / 20.0) * 0.85 = 348.16 -> round = 348 < 512
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=20.0)
        assert chunk == 512  # min_chunk_tokens

    def test_calculate_chunk_size_respects_max_chunk(self, config, mock_llm):
        """Result should not exceed max_chunk_tokens."""
        config.max_chunk_tokens = 2000
        config.min_chunk_tokens = 100
        calculator = TokenChunkCalculator(mock_llm, config)

        # Low expansion -> large chunk
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=0.1)
        assert chunk == 2000  # max_chunk_tokens

    def test_calculate_chunk_size_context_limit_binds(self, config, mock_llm):
        """Context limit should bind when output budget allows large chunks."""
        config.max_output_tokens = 100000  # Large output budget
        config.max_chunk_tokens = 50000
        calculator = TokenChunkCalculator(mock_llm, config)

        # With low expansion, output budget allows huge chunk
        # But context limit: (131072 - 100 - 100000) * 0.85 = 30972 * 0.85 = 26326
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=0.5)
        assert chunk == 26326  # Bound by context

    def test_validate_response_not_truncated_under_threshold(
        self, calculator, mock_llm
    ):
        """Response under 95% of max_output should pass."""
        mock_llm.count_tokens.return_value = 7000  # 85% of 8192
        result = calculator.validate_response_not_truncated("translated text", 8192)
        assert result is True

    def test_validate_response_not_truncated_over_threshold(self, calculator, mock_llm):
        """Response over 95% of max_output should fail (warning)."""
        mock_llm.count_tokens.return_value = 8000  # 97.6% of 8192
        result = calculator.validate_response_not_truncated("translated text", 8192)
        assert result is False

    def test_validate_response_exact_threshold(self, calculator, mock_llm):
        """Response at exactly 95% should pass."""
        mock_llm.count_tokens.return_value = 7782  # 95% of 8192
        result = calculator.validate_response_not_truncated("translated text", 8192)
        assert result is True

    def test_custom_ratios_invalid_key_format_logs_warning(
        self, mock_llm, config, caplog
    ):
        """Malformed custom ratio keys should log warning and be skipped."""
        import logging

        caplog.set_level(logging.WARNING)

        custom_ratios = {
            "en-es": 1.30,  # valid
            "en": 1.50,  # invalid - missing target
            "en-es-fr": 1.20,  # invalid - too many parts
            "en-fr": 1.15,  # valid
        }
        TokenChunkCalculator(mock_llm, config, custom_ratios=custom_ratios)

        # Check warning was logged for invalid keys
        assert len(caplog.records) == 2
        assert "Invalid custom ratio key format: 'en'" in caplog.text
        assert "Invalid custom ratio key format: 'en-es-fr'" in caplog.text

        # Valid keys should still work
        # Note: custom ratios are not used since we removed config fallback
        # They only apply to _custom_ratios dict
        calc = TokenChunkCalculator(mock_llm, config, custom_ratios={"en-es": 1.25})
        assert calc.get_expansion_ratio("en", "es") == 1.25
