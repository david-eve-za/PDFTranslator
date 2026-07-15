"""Chunking and Normalization Configuration Models.

CUPID Principle: Predictable - Explicit configuration with validation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class EncodingType(str, Enum):
    """Supported token encoding types."""

    CL100K_BASE = "cl100k_base"
    O200K_BASE = "o200k_base"
    P50K_BASE = "p50k_base"
    R50K_BASE = "r50k_base"


class SplitStrategy(str, Enum):
    """Text splitting strategies."""

    TOKENS = "tokens"
    SENTENCES = "sentences"
    PARAGRAPHS = "paragraphs"
    CHARACTERS = "characters"


class NormalizationForm(str, Enum):
    """Unicode normalization forms."""

    NFC = "NFC"
    NFD = "NFD"
    NFKC = "NFKC"
    NFKD = "NFKD"


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """Configuration for text chunking.

    Invariants:
    - max_tokens > 0
    - overlap_tokens >= 0 and < max_tokens
    - min_tokens > 0 and <= max_tokens
    """

    max_tokens: int = 500
    overlap_tokens: int = 50
    min_tokens: int = 50
    encoding: EncodingType = EncodingType.CL100K_BASE
    split_strategy: SplitStrategy = SplitStrategy.TOKENS
    preserve_paragraphs: bool = True
    include_metadata: bool = True

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens must be >= 0")
        if self.overlap_tokens >= self.max_tokens:
            raise ValueError("overlap_tokens must be < max_tokens")
        if self.min_tokens <= 0:
            raise ValueError("min_tokens must be > 0")
        if self.min_tokens > self.max_tokens:
            raise ValueError("min_tokens must be <= max_tokens")

    @classmethod
    def for_translation(cls, target_model: str = "gpt-4") -> ChunkConfig:
        """Create config optimized for translation models."""
        return cls(
            max_tokens=512,
            overlap_tokens=64,
            min_tokens=100,
            encoding=EncodingType.CL100K_BASE,
        )

    @classmethod
    def for_embedding(cls, max_tokens: int = 8191) -> ChunkConfig:
        """Create config optimized for embedding models."""
        return cls(
            max_tokens=min(max_tokens, 8191),
            overlap_tokens=128,
            min_tokens=256,
            encoding=EncodingType.CL100K_BASE,
        )

    @classmethod
    def from_dict(cls, data: dict) -> ChunkConfig:
        """Create config from dictionary (for CLI/JSON)."""
        # Convert string enums
        if "encoding" in data and isinstance(data["encoding"], str):
            data["encoding"] = EncodingType(data["encoding"])
        if "split_strategy" in data and isinstance(data["split_strategy"], str):
            data["split_strategy"] = SplitStrategy(data["split_strategy"])
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "max_tokens": self.max_tokens,
            "overlap_tokens": self.overlap_tokens,
            "min_tokens": self.min_tokens,
            "encoding": self.encoding.value,
            "split_strategy": self.split_strategy.value,
            "preserve_paragraphs": self.preserve_paragraphs,
            "include_metadata": self.include_metadata,
        }


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Configuration for text normalization.

    Invariants:
    - unicode_form is a valid NormalizationForm
    - If lower_case is True, preserve_case must be False
    """

    unicode_form: NormalizationForm = NormalizationForm.NFC
    lower_case: bool = False
    strip_whitespace: bool = True
    collapse_whitespace: bool = True
    remove_control_chars: bool = True
    preserve_case: bool = False
    normalize_quotes: bool = True
    normalize_dashes: bool = True
    normalize_ellipsis: bool = True
    language: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lower_case and self.preserve_case:
            raise ValueError("Cannot both lower_case and preserve_case")

    @classmethod
    def for_translation(cls) -> NormalizationConfig:
        """Create config optimized for translation preprocessing."""
        return cls(
            unicode_form=NormalizationForm.NFC,
            lower_case=False,
            strip_whitespace=True,
            collapse_whitespace=True,
            remove_control_chars=True,
            preserve_case=True,
            normalize_quotes=True,
            normalize_dashes=True,
            normalize_ellipsis=True,
            language=None,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "unicode_form": self.unicode_form.value,
            "lower_case": self.lower_case,
            "strip_whitespace": self.strip_whitespace,
            "collapse_whitespace": self.collapse_whitespace,
            "remove_control_chars": self.remove_control_chars,
            "preserve_case": self.preserve_case,
            "normalize_quotes": self.normalize_quotes,
            "normalize_dashes": self.normalize_dashes,
            "normalize_ellipsis": self.normalize_ellipsis,
            "language": self.language,
        }