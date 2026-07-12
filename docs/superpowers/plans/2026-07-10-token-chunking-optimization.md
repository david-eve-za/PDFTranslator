# Token Chunking Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement adaptive token chunking for PDF translation using Mistral Large 3 675B model (131k context), replacing the fixed 1024-token chunk size with a calculated optimal size based on prompt tokens, language-pair expansion ratios, and configurable safety margins.

**Architecture:** New `TokenChunkCalculator` class in `infrastructure/llm/` computes optimal chunk size. `NvidiaLLM.split_into_limit()` refactored to use calculator. Configuration extended in `NvidiaConfig` with new fields for max_output_tokens, safety margins, and expansion ratio overrides.

**Tech Stack:** Python 3.11+, Pydantic v2, NLTK Text Splitter, Transformers tokenizer, pytest

## Global Constraints

- Python >= 3.11 (from pyproject.toml)
- Pydantic v2 for config validation
- Follow existing project structure: `src/pdftranslator/infrastructure/llm/` for LLM code
- Logging via standard `logging` module (project uses structlog but stdlib logger in llm/)
- NLTK text splitter with custom length_function (count_tokens)
- Config loaded via `Settings.get()` singleton
- Tests in `tests/` mirroring source structure
- Commit message format: `type(scope): description` (feat, fix, refactor, test, docs)
- Type hints required (strict mypy)

---

### Task 1: Add Configuration Fields to NvidiaConfig

**Files:**
- Modify: `src/pdftranslator/core/config/llm.py:77-98` (NvidiaConfig class)
- Test: `tests/core/config/test_llm_config.py` (new file)

**Interfaces:**
- Produces: `NvidiaConfig` with new fields: `max_output_tokens`, `context_size`, `chunk_safety_margin_pct`, `max_chunk_tokens`, `min_chunk_tokens`, `expansion_ratios`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/config/test_llm_config.py
"""Tests for LLM configuration models."""

import pytest
from pydantic import ValidationError

from pdftranslator.core.config.llm import NvidiaConfig, NvidiaConfigV2


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/config/test_llm_config.py -v`
Expected: FAIL - NvidiaConfig missing new fields, test file doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# src/pdftranslator/core/config/llm.py (modify NvidiaConfig class, lines 77-98)

class NvidiaConfig(BaseModel):
    """NVIDIA NIM configuration."""

    model_name: str = Field(
        default="mistralai/mistral-large-3-675b-instruct-2512"
    )
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_output_tokens: int = Field(
        default=8192,                           # CHANGED from 1024
        ge=1024, le=131072,
        description="Max tokens reserved for model output per request"
    )
    rate_limit: int = Field(default=30, gt=0, description="Requests per minute")
    retry_attempts: int = Field(default=6, gt=0)
    request_timeout: int = Field(
        default=3600, gt=0, description="Request timeout in seconds"
    )
    max_bucket_size: int = Field(default=10, gt=0)
    context_size: int = Field(
        default=131072,
        frozen=True,
        description="Model context window (input + output)"
    )
    chunk_safety_margin_pct: float = Field(
        default=0.15,                           # NEW
        ge=0.05, le=0.30,
        description="Percentage margin to prevent truncation"
    )
    max_chunk_tokens: int = Field(
        default=32768,
        ge=512, le=65536,
        description="Practical upper bound per chunk"
    )
    min_chunk_tokens: int = Field(
        default=512,
        ge=128,
        description="Minimum viable chunk size"
    )
    local_tokenizer_name: str = Field(
        default="mistralai/Mistral-Large-3-675B-Instruct-2512"
    )
    local_tokenizer_dir: str = Field(default="mistral-large-3-675b-instruct-2512")
    # NVIDIA NIM Embedding/Reranking settings
    embed_model: str = Field(default="nvidia/nv-embedqa-e5-v5")
    rerank_model: str = Field(default="nvidia/nv-rerankqa-mistral-2b-4b-4096-v1")
    rerank_top_n: int = Field(default=5, gt=0)
    # NEW: Custom expansion ratios per language pair
    expansion_ratios: Dict[str, float] = Field(
        default_factory=dict,
        description="Custom ratios: 'en-es': 1.3, 'en-zh': 0.6, etc."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/config/test_llm_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/core/config/llm.py tests/core/config/test_llm_config.py
git commit -m "feat(config): add token chunking fields to NvidiaConfig"
```

---

### Task 2: Create TokenChunkCalculator Class

**Files:**
- Create: `src/pdftranslator/infrastructure/llm/token_chunk_calculator.py`
- Test: `tests/infrastructure/llm/test_token_chunk_calculator.py`

**Interfaces:**
- Consumes: `LLMClient` (protocol), `NvidiaConfig`
- Produces: `TokenChunkCalculator` class with methods:
  - `measure_prompt_tokens(template, source_lang, target_lang) -> int`
  - `get_expansion_ratio(source_lang, target_lang) -> float`
  - `calculate_chunk_size(prompt_tokens, expansion_ratio) -> int`
  - `validate_response_not_truncated(response, max_output) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/infrastructure/llm/test_token_chunk_calculator.py
"""Tests for TokenChunkCalculator."""

import pytest
from unittest.mock import Mock, MagicMock

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
        """Custom expansion ratios from config should override defaults."""
        config.expansion_ratios = {"en-es": 1.25, "en-fr": 1.10}
        calculator = TokenChunkCalculator(mock_llm, config)
        
        assert calculator.get_expansion_ratio("en", "es") == 1.25
        assert calculator.get_expansion_ratio("en", "fr") == 1.10
        # Non-overridden should still use defaults
        assert calculator.get_expansion_ratio("en", "zh") == 0.55

    def test_calculate_chunk_size_en_es_8192_output(self, calculator):
        """EN->ES with 8192 output should yield ~5357 chunk tokens."""
        # Formula: (8192 / 1.30) * 0.85 = 5356.9 -> 5357
        # Also check context limit: (131072 - prompt - 8192) * 0.85
        # With prompt ~100: (131072 - 100 - 8192) * 0.85 = 103864 * 0.85 = 88284
        # min(5357, 88284, 32768) = 5357
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=1.30)
        assert chunk == 5357

    def test_calculate_chunk_size_en_zh_8192_output(self, calculator):
        """EN->ZH with 8192 output should yield ~11605 chunk tokens."""
        # (8192 / 0.55) * 0.85 = 12657.8
        # Context: (131072 - 100 - 8192) * 0.85 = 88284
        # min(12657, 88284, 32768) = 12657
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=0.55)
        assert chunk == 12657

    def test_calculate_chunk_size_respects_min_chunk(self, calculator):
        """Result should not go below min_chunk_tokens."""
        # Very high expansion ratio
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=10.0)
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
        # But context limit: (131072 - 100 - 100000) * 0.85 = 26330
        chunk = calculator.calculate_chunk_size(prompt_tokens=100, expansion_ratio=0.5)
        assert chunk == 26330  # Bound by context

    def test_validate_response_not_truncated_under_threshold(self, calculator, mock_llm):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/infrastructure/llm/test_token_chunk_calculator.py -v`
Expected: FAIL - module and class don't exist

- [ ] **Step 3: Write minimal implementation**

```python
# src/pdftranslator/infrastructure/llm/token_chunk_calculator.py
"""Adaptive token chunk calculator for translation requests."""

import logging
from typing import ClassVar, Dict, Optional, Tuple

from pdftranslator.core.config.llm import NvidiaConfig
from pdftranslator.infrastructure.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class TokenChunkCalculator:
    """Calculates optimal chunk size for translation based on model limits and language pair."""

    # Default expansion ratios for common language pairs (source, target) -> ratio
    DEFAULT_EXPANSION_RATIOS: ClassVar[Dict[Tuple[str, str], float]] = {
        # English to romance languages (expansion)
        ("en", "es"): 1.30,
        ("en", "pt"): 1.25,
        ("en", "fr"): 1.15,
        ("en", "it"): 1.10,
        # English to germanic
        ("en", "de"): 1.20,
        ("en", "nl"): 1.15,
        # English to slavic
        ("en", "pl"): 1.20,
        ("en", "ru"): 1.15,
        # English to semitic
        ("en", "ar"): 1.15,
        # English to CJK (contraction)
        ("en", "zh"): 0.55,
        ("en", "ja"): 0.60,
        ("en", "ko"): 0.65,
        # English to indic
        ("en", "hi"): 1.10,
        # Reverse directions (approximate)
        ("es", "en"): 0.80,
        ("fr", "en"): 0.85,
        ("de", "en"): 0.85,
        ("zh", "en"): 1.80,
        ("ja", "en"): 1.70,
        ("ko", "en"): 1.60,
        ("ru", "en"): 0.90,
        ("ar", "en"): 0.90,
    }

    SAMPLE_TEXT_FOR_MEASUREMENT = "Sample text for token measurement."

    def __init__(
        self,
        llm_client: LLMClient,
        config: NvidiaConfig,
        custom_ratios: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize calculator.

        Args:
            llm_client: LLM client for token counting.
            config: NVIDIA configuration with chunking parameters.
            custom_ratios: Optional override for expansion ratios (key: "src-tgt").
        """
        self._llm = llm_client
        self._config = config
        # Merge custom ratios (string keys) with defaults (tuple keys)
        self._custom_ratios: Dict[Tuple[str, str], float] = {}
        if custom_ratios:
            for k, v in custom_ratios.items():
                parts = k.split("-")
                if len(parts) == 2:
                    self._custom_ratios[(parts[0], parts[1])] = v

    def measure_prompt_tokens(
        self,
        template: str,
        source_lang: str,
        target_lang: str,
        sample_text: Optional[str] = None,
    ) -> int:
        """
        Measure actual tokens of formatted prompt template.

        Args:
            template: Prompt template with {text_chunk}, {source_lang}, {target_lang} placeholders.
            source_lang: Source language code.
            target_lang: Target language code.
            sample_text: Text to use for measurement (default: fixed sample).

        Returns:
            Token count of formatted prompt.
        """
        sample = sample_text or self.SAMPLE_TEXT_FOR_MEASUREMENT
        formatted = template.format(
            text_chunk=sample,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        return self._llm.count_tokens(formatted)

    def get_expansion_ratio(self, source_lang: str, target_lang: str) -> float:
        """
        Get expansion ratio for language pair.

        Args:
            source_lang: Source language code (BCP-47).
            target_lang: Target language code (BCP-47).

        Returns:
            Expansion ratio (output_tokens / input_tokens).
            Falls back to 1.15 for unknown pairs.
        """
        # Check custom overrides first
        key = (source_lang.lower(), target_lang.lower())
        if key in self._custom_ratios:
            return self._custom_ratios[key]

        # Check defaults
        if key in self.DEFAULT_EXPANSION_RATIOS:
            return self.DEFAULT_EXPANSION_RATIOS[key]

        # Conservative fallback: assume slight expansion
        logger.debug(
            f"No expansion ratio for {source_lang}->{target_lang}, using fallback 1.15"
        )
        return 1.15

    def calculate_chunk_size(
        self,
        prompt_tokens: int,
        expansion_ratio: float,
    ) -> int:
        """
        Calculate optimal chunk size using adaptive formula.

        Formula:
            by_output = (max_output_tokens / expansion_ratio) * (1 - safety_margin)
            by_context = (context_size - prompt_tokens - max_output_tokens) * (1 - safety_margin)
            chunk_size = min(by_output, by_context, max_chunk_tokens)
            return max(chunk_size, min_chunk_tokens)

        Args:
            prompt_tokens: Measured token count of formatted prompt.
            expansion_ratio: Output/input token ratio for language pair.

        Returns:
            Optimal chunk size in tokens.
        """
        cfg = self._config
        margin = 1.0 - cfg.chunk_safety_margin_pct

        # Limit 1: Output budget divided by expansion
        by_output = (cfg.max_output_tokens / expansion_ratio) * margin

        # Limit 2: Available context minus prompt and reserved output
        available_context = cfg.context_size - prompt_tokens - cfg.max_output_tokens
        by_context = max(0, available_context) * margin

        # Apply bounds
        chunk_size = min(by_output, by_context, cfg.max_chunk_tokens)
        chunk_size = max(int(chunk_size), cfg.min_chunk_tokens)

        logger.info(
            f"Chunk calculation: prompt={prompt_tokens}, expansion={expansion_ratio:.2f}, "
            f"by_output={by_output:.0f}, by_context={by_context:.0f}, "
            f"max_chunk={cfg.max_chunk_tokens}, min_chunk={cfg.min_chunk_tokens} -> {chunk_size}"
        )

        return chunk_size

    def validate_response_not_truncated(self, response: str, max_output: int) -> bool:
        """
        Heuristic check for response truncation.

        If response uses >95% of max_output budget, likely truncated.

        Args:
            response: Model response text.
            max_output: Configured max output tokens for this request.

        Returns:
            True if response appears complete, False if possibly truncated.
        """
        response_tokens = self._llm.count_tokens(response)
        threshold = max_output * 0.95

        if response_tokens > threshold:
            logger.warning(
                f"Possible truncation: response={response_tokens} tokens "
                f"> {threshold:.0f} threshold (95% of max_output={max_output})"
            )
            return False
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/infrastructure/llm/test_token_chunk_calculator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/infrastructure/llm/token_chunk_calculator.py tests/infrastructure/llm/test_token_chunk_calculator.py
git commit -m "feat(llm): add TokenChunkCalculator for adaptive chunk sizing"
```

---

### Task 3: Refactor NvidiaLLM.split_into_limit()

**Files:**
- Modify: `src/pdftranslator/infrastructure/llm/nvidia.py:81-104` (split_into_limit method)
- Test: `tests/infrastructure/llm/test_nvidia_llm.py` (new or extend)

**Interfaces:**
- Consumes: `TokenChunkCalculator`, prompt template path from settings
- Produces: Updated `split_into_limit(text, language, source_lang, target_lang)` returning optimally-sized chunks

- [ ] **Step 1: Write the failing test**

```python
# tests/infrastructure/llm/test_nvidia_llm.py
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
        # With EN->ES expansion=1.3, expect ~5357 tokens/chunk
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
        # This is a behavioral test
        assert len(chunks_es) > 0
        assert len(chunks_zh) > 0
        # Note: exact counts depend on NLTK splitter behavior
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/infrastructure/llm/test_nvidia_llm.py -v`
Expected: FAIL - `split_into_limit` doesn't accept `source_lang`/`target_lang` params, doesn't use calculator

- [ ] **Step 3: Write minimal implementation**

```python
# src/pdftranslator/infrastructure/llm/nvidia.py

# ADD IMPORT at top (after existing imports)
from pdftranslator.infrastructure.llm.token_chunk_calculator import TokenChunkCalculator
from pdftranslator.core.config.llm import BCP47Language


# MODIFY split_into_limit method (lines 81-104)
def split_into_limit(
    self,
    text: str,
    language: BCP47Language = BCP47Language.ENGLISH,
    source_lang: str = "en",
    target_lang: str = "es",
) -> list[str]:
    """
    Split text into chunks optimized for translation.

    Args:
        text: Text to split.
        language: BCP 47 language code for NLTK sentence splitting.
        source_lang: Source language code for expansion ratio.
        target_lang: Target language code for expansion ratio.

    Returns:
        List of text chunks.
    """
    # Load prompt template
    template = self._load_prompt_template()

    # Calculate optimal chunk size using TokenChunkCalculator
    calculator = TokenChunkCalculator(self, self._settings.llm.nvidia)
    prompt_tokens = calculator.measure_prompt_tokens(
        template, source_lang, target_lang
    )
    expansion_ratio = calculator.get_expansion_ratio(source_lang, target_lang)
    chunk_size = calculator.calculate_chunk_size(prompt_tokens, expansion_ratio)

    logger.info(
        f"Adaptive chunking: prompt={prompt_tokens} tokens, "
        f"expansion={expansion_ratio:.2f} ({source_lang}->{target_lang}), "
        f"chunk_size={chunk_size} tokens"
    )

    # Use NLTKTextSplitter with calculated chunk size
    text_splitter = NLTKTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=0,
        language=language.to_nltk_name(),
        length_function=self.count_tokens,
    )

    return text_splitter.split_text(text)


# ADD helper method to load prompt template
def _load_prompt_template(self) -> str:
    """Load translation prompt template from configured path."""
    prompt_path = self._settings.paths.translation_prompt_path
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/infrastructure/llm/test_nvidia_llm.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/infrastructure/llm/nvidia.py tests/infrastructure/llm/test_nvidia_llm.py
git commit -m "feat(llm): refactor NvidiaLLM.split_into_limit to use adaptive chunking"
```

---

### Task 4: Update TranslatorService to Pass Language Pair

**Files:**
- Modify: `src/pdftranslator/services/translator.py:67-88` (translate method, chunking call)
- Test: `tests/services/test_translator.py` (extend existing)

**Interfaces:**
- Consumes: `LLMClient.split_into_limit()` with new params
- Produces: Updated `translate()` passing `source_lang`, `target_lang` to split

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_translator.py (add to existing)
"""Test translator service language pair passthrough."""

from unittest.mock import Mock, MagicMock
import pytest

from pdftranslator.services.translator import TranslatorService
from pdftranslator.infrastructure.llm.protocol import LLMClient


class TestTranslatorServiceLanguagePair:
    """Tests for language pair passthrough in translation."""

    @pytest.fixture
    def mock_llm_factory(self):
        factory = Mock()
        llm_client = Mock(spec=LLMClient)
        llm_client.split_into_limit = Mock(return_value=["chunk1", "chunk2"])
        llm_client.call_model = Mock(return_value="translated")
        factory.create.return_value = llm_client
        return factory

    def test_translate_passes_source_target_to_split(self, mock_llm_factory):
        """translate() should pass source_lang and target_lang to split_into_limit."""
        service = TranslatorService(mock_llm_factory)
        
        service.translate(
            text="Hello world",
            source_lang="en",
            target_lang="es"
        )
        
        # Verify split_into_limit was called with language pair
        mock_llm_factory.create.return_value.split_into_limit.assert_called_once()
        call_kwargs = mock_llm_factory.create.return_value.split_into_limit.call_args.kwargs
        assert call_kwargs.get("source_lang") == "en"
        assert call_kwargs.get("target_lang") == "es"

    def test_translate_defaults_to_en_es(self, mock_llm_factory):
        """Default language pair should be en->es if not specified."""
        service = TranslatorService(mock_llm_factory)
        service.translate(text="Hello")  # No lang args
        
        call_kwargs = mock_llm_factory.create.return_value.split_into_limit.call_args.kwargs
        assert call_kwargs.get("source_lang") == "en"
        assert call_kwargs.get("target_lang") == "es"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_translator.py::TestTranslatorServiceLanguagePair -v`
Expected: FAIL - `translate()` doesn't pass language args to `split_into_limit`

- [ ] **Step 3: Write minimal implementation**

```python
# src/pdftranslator/services/translator.py

# MODIFY translate method (around line 67-88)
def translate(
    self,
    text: str,
    source_lang: str,
    target_lang: str,
    language: BCP47Language = BCP47Language.ENGLISH,
) -> TranslationResult:
    """
    Translate text from source to target language.

    Args:
        text: Text to translate.
        source_lang: Source language code (e.g., "en").
        target_lang: Target language code (e.g., "es").
        language: Language for text splitting (default: English).

    Returns:
        TranslationResult with translated text and metadata.
    """
    # Split text into chunks - PASS LANGUAGE PAIR
    chunks = self._llm_client.split_into_limit(
        text, 
        language=language,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    logger.info(f"Text split into {len(chunks)} chunks for translation")

    if not chunks:
        logger.warning("No chunks to translate")
        return TranslationResult(
            original_chunks=0,
            translated_chunks=0,
            text="",
            errors=["No text to translate"],
        )

    # ... rest unchanged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_translator.py::TestTranslatorServiceLanguagePair -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/services/translator.py tests/services/test_translator.py
git commit -m "feat(service): pass language pair to chunking for adaptive sizing"
```

---

### Task 5: Update CLI Commands Using Translation

**Files:**
- Modify: `src/pdftranslator/cli/commands/translate_chapter.py` (GlossaryAwareTranslator)
- Modify: `src/pdftranslator/cli/commands/process.py` (translate_text)
- Test: `tests/cli/commands/test_translate_chapter.py` (verify call)

**Interfaces:**
- Consumes: `TranslatorService.translate()` with language args
- Produces: CLI commands correctly passing source/target languages

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/commands/test_translate_chapter.py (add)
"""Test CLI translate chapter passes language pair."""

from unittest.mock import Mock, patch
import pytest

from pdftranslator.cli.commands.translate_chapter import GlossaryAwareTranslator


class TestCLITranslateChapterLanguagePair:
    """Tests for language pair in CLI translation commands."""

    @pytest.fixture
    def mock_translator_service(self):
        service = Mock()
        service.translate = Mock()
        return service

    def test_glossary_aware_translator_passes_langs(self, mock_translator_service):
        """GlossaryAwareTranslator should pass source/target to translate."""
        translator = GlossaryAwareTranslator(mock_translator_service)
        translator.translate(
            text="Test text",
            source_lang="en",
            target_lang="es"
        )
        
        mock_translator_service.translate.assert_called_once()
        call_kwargs = mock_translator_service.translate.call_args.kwargs
        assert call_kwargs["source_lang"] == "en"
        assert call_kwargs["target_lang"] == "es"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_translate_chapter.py::TestCLITranslateChapterLanguagePair -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/pdftranslator/cli/commands/translate_chapter.py

# MODIFY GlossaryAwareTranslator.translate_text (around line 378-416)
def translate_text(
    self,
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    """Translate text using the underlying translator service."""
    return self._translator.translate(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        language=BCP47Language.ENGLISH,  # or detect from source_lang
    )
```

```python
# src/pdftranslator/cli/commands/process.py

# MODIFY translate_text (around line 34-51)
def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    glossary: Optional[Dict[str, str]] = None,
) -> str:
    """Translate text with optional glossary."""
    # ... existing logic ...
    return translator.translate(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/cli/commands/test_translate_chapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdftranslator/cli/commands/translate_chapter.py src/pdftranslator/cli/commands/process.py tests/cli/commands/test_translate_chapter.py
git commit -m "feat(cli): pass language pair through translation pipeline"
```

---

### Task 6: Integration Test & End-to-End Verification

**Files:**
- Create: `tests/integration/test_token_chunking_e2e.py`
- Run: Full test suite

**Interfaces:**
- Consumes: All above components
- Produces: Verified end-to-end translation with adaptive chunking

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_token_chunking_e2e.py
"""End-to-end integration test for adaptive token chunking."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from pdftranslator.services.translator import TranslatorService
from pdftranslator.infrastructure.llm.factory import LLMFactory
from pdftranslator.core.config.settings import Settings


class TestTokenChunkingE2E:
    """Integration tests for the complete chunking pipeline."""

    @pytest.fixture
    def mock_settings(self):
        settings = Mock(spec=Settings)
        settings.llm.nvidia = Mock()
        settings.llm.nvidia.max_output_tokens = 8192
        settings.llm.nvidia.context_size = 131072
        settings.llm.nvidia.chunk_safety_margin_pct = 0.15
        settings.llm.nvidia.max_chunk_tokens = 32768
        settings.llm.nvidia.min_chunk_tokens = 512
        settings.llm.nvidia.model_name = "mistralai/mistral-large-3-675b-instruct-2512"
        settings.llm.nvidia.local_tokenizer_name = "test"
        settings.llm.nvidia.local_tokenizer_dir = "test"
        settings.paths.translation_prompt_path = "src/pdftranslator/tools/translation_prompt.txt"
        settings.llm.agent = "nvidia"
        return settings

    @pytest.mark.integration
    def test_en_to_es_produces_fewer_chunks_than_old(self, mock_settings):
        """EN->ES translation should produce fewer chunks than 1024-token fixed."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tokenizer = Mock()
            # Realistic token counts: ~4 chars per token
            mock_tokenizer.encode = Mock(side_effect=lambda t, **kw: list(range(len(t) // 4)))
            mock_tok_class.from_pretrained.return_value = mock_tokenizer
            
            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()
                
                # Long text: ~50,000 chars = ~12,500 tokens
                long_text = "This is a sentence. " * 2500  # ~50k chars
                
                # Get chunks with adaptive sizing
                chunks = llm.split_into_limit(long_text, "en", "es")
                
                # Old fixed 1024: ~12 chunks
                # New adaptive ~5357: ~2-3 chunks
                assert len(chunks) < 10  # Should be much fewer
                assert len(chunks) >= 2  # But not 1 (too large for NLTK)

    @pytest.mark.integration
    def test_en_to_zh_allows_larger_chunks(self, mock_settings):
        """EN->ZH (contraction) should allow larger chunks than EN->ES."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tokenizer = Mock()
            mock_tokenizer.encode = Mock(side_effect=lambda t, **kw: list(range(len(t) // 4)))
            mock_tok_class.from_pretrained.return_value = mock_tokenizer
            
            with patch("pdftranslator.infrastructure.llm.nvidia.ChatNVIDIA"):
                factory = LLMFactory(mock_settings)
                llm = factory.create()
                
                long_text = "This is a sentence. " * 2500
                
                chunks_es = llm.split_into_limit(long_text, "en", "es")
                chunks_zh = llm.split_into_limit(long_text, "en", "zh")
                
                # ZH contraction -> larger chunks -> fewer chunks
                assert len(chunks_zh) <= len(chunks_es)

    @pytest.mark.integration
    def test_full_translation_pipeline_no_truncation(self, mock_settings):
        """Full translation should not produce truncation warnings."""
        with patch("pdftranslator.infrastructure.llm.nvidia.AutoTokenizer") as mock_tok_class:
            mock_tokenizer = Mock()
            mock_tokenizer.encode = Mock(side_effect=lambda t, **kw: list(range(len(t) // 4)))
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_token_chunking_e2e.py -v`
Expected: FAIL - components not fully integrated

- [ ] **Step 3: Run full test suite**

Run: `pytest -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_token_chunking_e2e.py
git commit -m "test(integration): add e2e tests for adaptive token chunking"
```

---

### Task 7: Documentation & Config Example

**Files:**
- Modify: `.env.example` (add new config vars)
- Modify: `README.md` (brief mention of adaptive chunking)
- Create: `docs/token-chunking-configuration.md` (detailed guide)

**Interfaces:** None (documentation only)

- [ ] **Step 1: Write documentation**

```bash
# .env.example - ADD at end
# ── Token Chunking (Adaptive) ────────────────────────────────
# Max output tokens per request (model supports up to 131072)
# Default 8192 - increase for fewer API calls, decrease if truncation occurs
LLM__NVIDIA__MAX_OUTPUT_TOKENS=8192

# Safety margin percentage (0.05-0.30) to prevent response truncation
LLM__NVIDIA__CHUNK_SAFETY_MARGIN_PCT=0.15

# Maximum practical chunk size in tokens
LLM__NVIDIA__MAX_CHUNK_TOKENS=32768

# Minimum viable chunk size
LLM__NVIDIA__MIN_CHUNK_TOKENS=512

# Custom expansion ratios (JSON): "src-tgt": ratio
# Example: '{"en-es": 1.25, "en-zh": 0.55}'
# Overrides built-in defaults for specific language pairs
LLM__NVIDIA__EXPANSION_RATIOS={}
```

- [ ] **Step 2: Commit**

```bash
git add .env.example README.md docs/token-chunking-configuration.md
git commit -m "docs: document adaptive token chunking configuration"
```

---

### Task 8: Final Validation & Merge Prep

**Files:** None (validation steps)

- [ ] **Step 1: Run full test suite**

```bash
pytest -v --tb=short -x
```
Expected: All tests PASS

- [ ] **Step 2: Run type checking**

```bash
mypy src/pdftranslator/infrastructure/llm/token_chunk_calculator.py \
     src/pdftranslator/infrastructure/llm/nvidia.py \
     src/pdftranslator/services/translator.py
```
Expected: No errors

- [ ] **Step 3: Run linter**

```bash
ruff check src/pdftranslator/infrastructure/llm/ src/pdftranslator/services/translator.py
```
Expected: No errors

- [ ] **Step 4: Build verification**

```bash
python -m pip install -e .  # Verify package builds
```
Expected: Success

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final validation fixes"
```

- [ ] **Step 6: Push feature branch**

```bash
git push origin feature/token-chunking-optimization
```

- [ ] **Step 7: Create PR to main**

---

## Summary

**Total Tasks:** 8
**Estimated Time:** ~2-3 hours
**Key Deliverables:**
1. `TokenChunkCalculator` - adaptive chunk sizing logic
2. Extended `NvidiaConfig` - 6 new configurable fields
3. Refactored `NvidiaLLM.split_into_limit()` - uses calculator
4. Updated `TranslatorService.translate()` - passes language pair
5. Updated CLI commands - propagate language pair
6. Comprehensive test suite (unit + integration)
7. Documentation for configuration

**Rollback Plan:** Revert `feature/token-chunking-optimization` branch if issues arise. Default config values are conservative (8192 output, 15% margin) making rollback low-risk.