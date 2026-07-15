"""Text Normalization Utilities.

CUPID Principle: Unix Philosophy - Simple composable text transforms.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Configuration for text normalization."""

    unicode_normalize: bool = True
    normalize_form: str = "NFKC"
    remove_control_chars: bool = True
    collapse_whitespace: bool = True
    normalize_line_endings: bool = True
    strip_margin: bool = False
    margin_char: str = "|"
    lower_case: bool = False
    remove_duplicate_punctuation: bool = False

    def __post_init__(self) -> None:
        if self.normalize_form not in ("NFC", "NFD", "NFKC", "NFKD"):
            raise ValueError("normalize_form must be NFC, NFD, NFKC, or NFKD")


class TextNormalizer:
    """Composable text normalization pipeline.

    Each method is a pure function - compose as needed.
    """

    def __init__(self, config: Optional[NormalizationConfig] = None):
        self._config = config or NormalizationConfig()

    def normalize(self, text: str) -> str:
        """Apply all configured normalizations."""
        result = text

        if self._config.unicode_normalize:
            result = self._normalize_unicode(result)

        if self._config.remove_control_chars:
            result = self._remove_control_chars(result)

        if self._config.collapse_whitespace:
            result = self._collapse_whitespace(result)

        if self._config.normalize_line_endings:
            result = self._normalize_line_endings(result)

        if self._config.strip_margin:
            result = self._strip_margin(result)

        if self._config.lower_case:
            result = result.lower()

        if self._config.remove_duplicate_punctuation:
            result = self._remove_duplicate_punctuation(result)

        return result.strip()

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters."""
        return unicodedata.normalize(self._config.normalize_form, text)

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

    def _normalize_line_endings(self, text: str) -> str:
        """Normalize all line endings to \n."""
        return text.replace("\r\n", "\n").replace("\r", "\n")

    def _strip_margin(self, text: str) -> str:
        """Strip margin characters from multi-line strings."""
        lines = text.split("\n")
        processed = []
        for line in lines:
            index = line.find(self._config.margin_char)
            if index >= 0:
                processed.append(line[index + 1 :])
            else:
                processed.append(line)
        return "\n".join(processed)

    def _remove_duplicate_punctuation(self, text: str) -> str:
        """Remove repeated punctuation marks."""
        # Replace 3+ same punctuation with 2
        return re.sub(r"([.!?]){3,}", r"\1\1", text)


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