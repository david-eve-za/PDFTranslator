"""Text Normalization Utilities.

CUPID Principle: Unix Philosophy - Simple composable text transforms.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional
from dataclasses import dataclass, field

from ..models.config import NormalizationConfig, NormalizationForm


# Re-export the models config for backward compatibility
__all__ = ["TextNormalizer", "NormalizationConfig", "NormalizationForm"]


class TextNormalizer:
    """Composable text normalization pipeline.

    Each method is a pure function - compose as needed.
    """

    def __init__(self, config: Optional[NormalizationConfig] = None):
        self._config = config or NormalizationConfig.for_translation()

    def normalize(self, text: str) -> str:
        """Apply all configured normalizations."""
        result = text

        if self._config.unicode_form:
            result = self._normalize_unicode(result)

        if self._config.remove_control_chars:
            result = self._remove_control_chars(result)

        if self._config.collapse_whitespace:
            result = self._collapse_whitespace(result)

        if self._config.strip_whitespace:
            result = result.strip()

        if self._config.lower_case:
            result = result.lower()

        if self._config.normalize_quotes:
            result = self._normalize_quotes(result)

        if self._config.normalize_dashes:
            result = self._normalize_dashes(result)

        if self._config.normalize_ellipsis:
            result = self._normalize_ellipsis(result)

        return result

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters."""
        return unicodedata.normalize(self._config.unicode_form.value, text)

    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters except common whitespace."""
        # Keep: \n \r \t
        return "".join(
            ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or unicodedata.category(ch)[0] != "C"
        )

    def _collapse_whitespace(self, text: str) -> str:
        """Collapse multiple whitespace into single space."""
        # Preserve line breaks
        lines = text.split("\n")
        processed = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
        return "\n".join(processed)

    def _normalize_quotes(self, text: str) -> str:
        """Normalize smart quotes to straight quotes."""
        return text.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")

    def _normalize_dashes(self, text: str) -> str:
        """Normalize em/en dashes to hyphen."""
        return text.replace("—", "-").replace("–", "-")

    def _normalize_ellipsis(self, text: str) -> str:
        """Normalize ellipsis character to three dots."""
        return text.replace("…", "...")


# Convenience functions for direct use
def normalize_unicode(text: str, form: str = "NFKC") -> str:
    return unicodedata.normalize(form, text)


def remove_control_chars(text: str) -> str:
    return "".join(
        ch for ch in text if ch in "\n\r\t" or unicodedata.category(ch)[0] != "C"
    )


def collapse_whitespace(text: str, preserve_newlines: bool = True) -> str:
    if preserve_newlines:
        lines = text.split("\n")
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in lines)
    return re.sub(r"\s+", " ", text).strip()


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_margin(text: str, margin_char: str = "|") -> str:
    lines = text.split("\n")
    return "\n".join(
        line[line.index(margin_char) + 1 :] if margin_char in line else line for line in lines
    )


def clean_for_tokenization(text: str) -> str:
    """Full cleanup for tokenization compatibility."""
    text = normalize_unicode(text, "NFKC")
    text = remove_control_chars(text)
    text = collapse_whitespace(text, preserve_newlines=True)
    text = normalize_line_endings(text)
    return text.strip()