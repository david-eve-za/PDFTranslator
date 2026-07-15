"""Text Processing Core Package.

CUPID Principle: Composable - Modular core components.
"""

from .chunker import TextChunker, Tokenizer
from .overlap import OverlapHandler, OverlapResult
from .normalizer import TextNormalizer, NormalizationForm, clean_for_tokenization

__all__ = [
    "TextChunker",
    "Tokenizer",
    "OverlapHandler",
    "OverlapResult",
    "TextNormalizer",
    "NormalizationForm",
    "clean_for_tokenization",
]