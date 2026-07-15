"""Token-Based Text Chunker.

CUPID Principles:
- Composable: Pure functions, no external deps
- Unix Philosophy: Single responsibility (chunk by tokens)
- Predictable: Deterministic output, validated config
- Idiomatic: Python 3.12+, type hints, dataclasses
- Domain-Focused: Text chunking domain logic only
"""

from __future__ import annotations
from typing import Optional
import tiktoken

from ..models.chunk import TextChunk, ChunkResult
from ..models.config import ChunkConfig, EncodingType, SplitStrategy


class Tokenizer:
    """Tokenizer wrapper for consistent token counting."""

    _cache: dict[EncodingType, "Tokenizer"] = {}

    def __init__(self, encoding: EncodingType = EncodingType.CL100K_BASE):
        self._encoding = encoding
        self._tokenizer = tiktoken.get_encoding(encoding.value)

    @classmethod
    def get(cls, encoding: EncodingType = EncodingType.CL100K_BASE) -> "Tokenizer":
        """Get cached tokenizer instance."""
        if encoding not in cls._cache:
            cls._cache[encoding] = cls(encoding)
        return cls._cache[encoding]

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._tokenizer.encode(text))

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._tokenizer.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._tokenizer.decode(tokens)

    def encode_ordinary(self, text: str) -> list[int]:
        """Encode without special tokens."""
        return self._tokenizer.encode_ordinary(text)


class TextChunker:
    """Deterministic token-based text chunker with overlap.

    Provides predictable chunking algorithm suitable for:
    - LLM context window management
    - Embedding model input preparation
    - Translation pipeline segmentation
    """

    def __init__(self, config: Optional[ChunkConfig] = None):
        self._config = config or ChunkConfig()
        self._tokenizer = Tokenizer.get(self._config.encoding)

    @property
    def config(self) -> ChunkConfig:
        return self._config

    def chunk(self, text: str) -> ChunkResult:
        """Chunk text according to configuration.

        Args:
            text: Input text to chunk.

        Returns:
            ChunkResult with chunks and statistics.

        Note: Deterministic - same input + config always produces same output.
        """
        if not text or not text.strip():
            return ChunkResult.from_chunks([], self._config)

        text = text.strip()

        # Select chunking strategy
        if self._config.split_strategy == SplitStrategy.TOKENS:
            return self._chunk_by_tokens(text)
        elif self._config.split_strategy == SplitStrategy.SENTENCES:
            return self._chunk_by_sentences(text)
        elif self._config.split_strategy == SplitStrategy.PARAGRAPHS:
            return self._chunk_by_paragraphs(text)
        elif self._config.split_strategy == SplitStrategy.CHARACTERS:
            return self._chunk_by_characters(text)
        else:
            return self._chunk_by_tokens(text)

    def _chunk_by_tokens(self, text: str) -> ChunkResult:
        """Chunk by token count with overlap."""
        tokens = self._tokenizer.encode_ordinary(text)
        chunks = []

        if len(tokens) <= self._config.max_tokens:
            # Single chunk
            chunk = TextChunk.create(
                text=text,
                token_count=len(tokens),
                sequence_number=0,
                char_start=0,
            )
            return ChunkResult.from_chunks([chunk], self._config)

        stride = self._config.max_tokens - self._config.overlap_tokens
        if stride <= 0:
            stride = self._config.max_tokens

        for i, start in enumerate(range(0, len(tokens), stride)):
            end = min(start + self._config.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]

            # Skip if chunk too small (except first and last)
            if len(chunk_tokens) < self._config.min_tokens and i > 0 and end < len(tokens):
                continue

            chunk_text = self._tokenizer.decode(chunk_tokens)

            # Calculate char positions (approximate)
            char_start = self._estimate_char_position(text, tokens, start)
            char_end = self._estimate_char_position(text, tokens, end)

            chunk = TextChunk.create(
                text=chunk_text,
                token_count=len(chunk_tokens),
                sequence_number=i,
                char_start=char_start,
                metadata={"start_token": start, "end_token": end},
            )
            chunks.append(chunk)

            if end >= len(tokens):
                break

        return ChunkResult.from_chunks(chunks, self._config)

    def _chunk_by_sentences(self, text: str) -> ChunkResult:
        """Chunk by sentence boundaries, respecting token limits."""
        import re

        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_tokens = []
        current_text = ""
        sequence = 0
        char_pos = 0

        for sentence in sentences:
            sentence_tokens = self._tokenizer.encode_ordinary(sentence)

            if not current_tokens:
                # First sentence in chunk
                current_tokens = sentence_tokens
                current_text = sentence
            elif len(current_tokens) + len(sentence_tokens) <= self._config.max_tokens:
                # Add to current chunk
                current_tokens.extend(sentence_tokens)
                current_text += " " + sentence
            else:
                # Emit current chunk
                if current_tokens:
                    chunk = TextChunk.create(
                        text=current_text,
                        token_count=len(current_tokens),
                        sequence_number=sequence,
                        char_start=char_pos,
                    )
                    chunks.append(chunk)
                    sequence += 1
                    char_pos += len(current_text) + 1

                # Start new chunk with overlap if possible
                if self._config.overlap_tokens > 0 and len(current_tokens) > self._config.overlap_tokens:
                    overlap_start = max(0, len(current_tokens) - self._config.overlap_tokens)
                    overlap_tokens = current_tokens[overlap_start:]
                    overlap_text = self._tokenizer.decode(overlap_tokens)
                    current_tokens = overlap_tokens + sentence_tokens
                    current_text = overlap_text + " " + sentence
                else:
                    current_tokens = sentence_tokens
                    current_text = sentence

        # Emit final chunk
        if current_tokens:
            chunk = TextChunk.create(
                text=current_text,
                token_count=len(current_tokens),
                sequence_number=sequence,
                char_start=char_pos,
            )
            chunks.append(chunk)

        return ChunkResult.from_chunks(chunks, self._config)

    def _chunk_by_paragraphs(self, text: str) -> ChunkResult:
        """Chunk by paragraph boundaries, respecting token limits."""
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_tokens = []
        current_text = ""
        sequence = 0
        char_pos = 0

        for para in paragraphs:
            para_tokens = self._tokenizer.encode_ordinary(para)

            if len(para_tokens) > self._config.max_tokens:
                # Paragraph too large, split it by tokens
                if current_tokens:
                    chunk = TextChunk.create(
                        text=current_text,
                        token_count=len(current_tokens),
                        sequence_number=sequence,
                        char_start=char_pos,
                    )
                    chunks.append(chunk)
                    sequence += 1
                    char_pos += len(current_text) + 1
                    current_tokens = []
                    current_text = ""

                # Split large paragraph using token chunking
                para_chunks = self._chunk_large_text(para, sequence)
                chunks.extend(para_chunks.chunks)
                sequence += len(para_chunks.chunks)
                continue

            if not current_tokens:
                current_tokens = para_tokens
                current_text = para
            elif len(current_tokens) + len(para_tokens) <= self._config.max_tokens:
                current_tokens.extend(para_tokens)
                current_text += "\n\n" + para
            else:
                # Emit current
                if current_tokens:
                    chunk = TextChunk.create(
                        text=current_text,
                        token_count=len(current_tokens),
                        sequence_number=sequence,
                        char_start=char_pos,
                    )
                    chunks.append(chunk)
                    sequence += 1
                    char_pos += len(current_text) + 2

                # Start new with overlap
                if self._config.overlap_tokens > 0 and len(current_tokens) > self._config.overlap_tokens:
                    overlap_start = max(0, len(current_tokens) - self._config.overlap_tokens)
                    overlap_tokens = current_tokens[overlap_start:]
                    overlap_text = self._tokenizer.decode(overlap_tokens)
                    current_tokens = overlap_tokens + para_tokens
                    current_text = overlap_text + "\n\n" + para
                else:
                    current_tokens = para_tokens
                    current_text = para

        if current_tokens:
            chunk = TextChunk.create(
                text=current_text,
                token_count=len(current_tokens),
                sequence_number=sequence,
                char_start=char_pos,
            )
            chunks.append(chunk)

        return ChunkResult.from_chunks(chunks, self._config)

    def _chunk_by_characters(self, text: str) -> ChunkResult:
        """Fallback: chunk by approximate character count."""
        # Estimate tokens per char (roughly 4 chars per token for English)
        chars_per_token = 4
        max_chars = self._config.max_tokens * chars_per_token
        overlap_chars = self._config.overlap_tokens * chars_per_token

        chunks = []
        for i, start in enumerate(range(0, len(text), max_chars - overlap_chars)):
            end = min(start + max_chars, len(text))
            chunk_text = text[start:end]

            # Refine to token boundary
            tokens = self._tokenizer.encode_ordinary(chunk_text)
            if len(tokens) > self._config.max_tokens:
                # Trim to token limit
                tokens = tokens[: self._config.max_tokens]
                chunk_text = self._tokenizer.decode(tokens)
                end = start + len(chunk_text)

            if len(chunk_text.strip()) == 0:
                continue

            token_count = self._tokenizer.count_tokens(chunk_text)

            chunk = TextChunk.create(
                text=chunk_text,
                token_count=token_count,
                sequence_number=i,
                char_start=start,
            )
            chunks.append(chunk)

            if end >= len(text):
                break

        return ChunkResult.from_chunks(chunks, self._config)

    def _chunk_large_text(self, text: str, start_sequence: int) -> ChunkResult:
        """Split large text using token-based chunking."""
        config = ChunkConfig(
            max_tokens=self._config.max_tokens,
            overlap_tokens=self._config.overlap_tokens,
            min_tokens=self._config.min_tokens,
            encoding=self._config.encoding,
            split_strategy=SplitStrategy.TOKENS,
        )
        chunker = TextChunker(config)
        result = chunker._chunk_by_tokens(text)

        # Renumber sequences
        renumbered = []
        for i, chunk in enumerate(result.chunks):
            renumbered.append(
                TextChunk.create(
                    text=chunk.text,
                    token_count=chunk.token_count,
                    sequence_number=start_sequence + i,
                    char_start=chunk.char_start,
                    metadata=chunk.metadata,
                )
            )
        return ChunkResult.from_chunks(renumbered, config)

    def _estimate_char_position(
        self, original: str, tokens: list[int], token_index: int
    ) -> int:
        """Estimate character position for token index."""
        if token_index <= 0:
            return 0
        if token_index >= len(tokens):
            return len(original)

        # Decode tokens up to index and measure
        partial_tokens = tokens[:token_index]
        partial_text = self._tokenizer.decode(partial_tokens)
        return len(partial_text)


# Alias for backward compatibility
Config = ChunkConfig