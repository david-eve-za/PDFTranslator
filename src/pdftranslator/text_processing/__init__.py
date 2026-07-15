"""Text Processing Library.

CUPID Principles:
- Composable: Modular components, dependency injection
- Unix Philosophy: stdin/stdout pipeline, single responsibility
- Predictable: Deterministic output, validated config
- Idiomatic: Python 3.12+, type hints, Click CLI
- Domain-Focused: Text processing domain only

Usage:
    from pdftranslator.text_processing import TextChunker, ChunkConfig
    chunker = TextChunker(ChunkConfig(max_tokens=500))
    result = chunker.chunk("Your text here")

CLI:
    cat input.txt | pdftranslator-text chunk --tokens 500 > chunks.json
"""

from .models import TextChunk, ChunkResult, ChunkConfig, EncodingType, SplitStrategy, NormalizationConfig, NormalizationForm
from .core import TextChunker, Tokenizer, OverlapHandler, TextNormalizer

__version__ = "0.1.0"

__all__ = [
    # Models
    "TextChunk",
    "ChunkResult",
    "ChunkConfig",
    "EncodingType",
    "SplitStrategy",
    "NormalizationConfig",
    "NormalizationForm",
    # Core
    "TextChunker",
    "Tokenizer",
    "OverlapHandler",
    "TextNormalizer",
]