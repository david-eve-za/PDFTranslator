"""Tests for LLM configuration models."""

import pytest
from pydantic import ValidationError

from pdftranslator.core.config.llm import NvidiaConfig


class TestNvidiaConfigTokenChunking:
    """Tests for new token chunking config fields."""

    def test_default_max_output_tokens_is_8192(self):
        """Default max_output_tokens should be 8192 (not 1024)."""
        config = NvidiaConfig()
        assert config.max_output_tokens == 8192

    def test_context_size_frozen_at_131072(self):
        """context_size should be frozen at model's context window."""
        config = NvidiaConfig()
        assert config.context_size == 131072

    def test_default_safety_margin_15_percent(self):
        """Default safety margin should be 15%."""
        config = NvidiaConfig()
        assert config.chunk_safety_margin_pct == 0.15

    def test_default_max_chunk_tokens_32768(self):
        """Default max_chunk_tokens should be 32768."""
        config = NvidiaConfig()
        assert config.max_chunk_tokens == 32768

    def test_default_min_chunk_tokens_512(self):
        """Default min_chunk_tokens should be 512."""
        config = NvidiaConfig()
        assert config.min_chunk_tokens == 512

    def test_expansion_ratios_default_empty_dict(self):
        """expansion_ratios should default to empty dict."""
        config = NvidiaConfig()
        assert config.expansion_ratios == {}

    def test_max_output_tokens_validation_min_1024(self):
        """max_output_tokens must be >= 1024."""
        with pytest.raises(ValidationError):
            NvidiaConfig(max_output_tokens=512)

    def test_max_output_tokens_validation_max_131072(self):
        """max_output_tokens cannot exceed context window."""
        with pytest.raises(ValidationError):
            NvidiaConfig(max_output_tokens=200000)

    def test_safety_margin_validation_bounds(self):
        """safety_margin_pct must be between 0.05 and 0.30."""
        with pytest.raises(ValidationError):
            NvidiaConfig(chunk_safety_margin_pct=0.01)
        with pytest.raises(ValidationError):
            NvidiaConfig(chunk_safety_margin_pct=0.50)

    def test_can_override_expansion_ratios_via_env(self):
        """expansion_ratios can be set via environment variable."""
        import os
        os.environ["LLM__NVIDIA__EXPANSION_RATIOS"] = '{"en-es": 1.25, "en-zh": 0.55}'
        try:
            config = NvidiaConfig()
            assert config.expansion_ratios == {"en-es": 1.25, "en-zh": 0.55}
        finally:
            del os.environ["LLM__NVIDIA__EXPANSION_RATIOS"]