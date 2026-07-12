"""Adaptive token chunk calculator for translation requests."""

import logging
from typing import ClassVar

from pdftranslator.core.config.llm import NvidiaConfig
from pdftranslator.infrastructure.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class TokenChunkCalculator:
    """Calculates optimal chunk size for translation based on model limits and language pair."""

    # Default expansion ratios for common language pairs (source, target) -> ratio
    DEFAULT_EXPANSION_RATIOS: ClassVar[dict[tuple[str, str], float]] = {
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
        custom_ratios: dict[str, float] | None = None,
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
        self._custom_ratios: dict[tuple[str, str], float] = {}
        if custom_ratios:
            for k, v in custom_ratios.items():
                parts = k.split("-")
                if len(parts) == 2:
                    self._custom_ratios[(parts[0].lower(), parts[1].lower())] = v
                else:
                    logger.warning(
                        "Invalid custom ratio key format: '%s'. Expected 'src-tgt' (e.g., 'en-es'). Skipping.",
                        k,
                    )

    def measure_prompt_tokens(
        self,
        template: str,
        source_lang: str,
        target_lang: str,
        sample_text: str | None = None,
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
            "No expansion ratio for %s->%s, using fallback 1.15",
            source_lang,
            target_lang,
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
        chunk_size = max(round(chunk_size), cfg.min_chunk_tokens)

        logger.info(
            "Chunk calculation: prompt=%s, expansion=%.2f, "
            "by_output=%.0f, by_context=%.0f, "
            "max_chunk=%s, min_chunk=%s -> %s",
            prompt_tokens,
            expansion_ratio,
            by_output,
            by_context,
            cfg.max_chunk_tokens,
            cfg.min_chunk_tokens,
            chunk_size,
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
                "Possible truncation: response=%s tokens > %.0f threshold (95%% of max_output=%s)",
                response_tokens,
                threshold,
                max_output,
            )
            return False
        return True
