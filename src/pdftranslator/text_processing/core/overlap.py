"""Overlap Handler for Chunk Context Preservation.

CUPID Principle: Composable - Pure functions for overlap management.
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field

from ..models.chunk import TextChunk
from ..models.config import ChunkConfig
from .chunker import Tokenizer


@dataclass(frozen=True, slots=True)
class OverlapResult:
    """Result of applying overlap to chunks."""

    chunks: tuple[TextChunk, ...]
    overlap_info: tuple[dict, ...]  # Per-chunk overlap metadata


class OverlapHandler:
    """Handle overlap between consecutive chunks for context preservation."""

    def __init__(self, config: ChunkConfig):
        self._config = config
        self._tokenizer = Tokenizer.get(config.encoding)

    @property
    def overlap_tokens(self) -> int:
        return self._config.overlap_tokens

    def apply_overlap(
        self,
        chunks: list[TextChunk],
        original_text: Optional[str] = None,
    ) -> OverlapResult:
        """Apply overlap between consecutive chunks.

        For each chunk (except first), prepend overlap_tokens from previous chunk.
        This ensures context continuity across chunk boundaries.

        Args:
            chunks: List of chunks to apply overlap to.
            original_text: Original full text (optional, for boundary verification).

        Returns:
            OverlapResult with modified chunks and overlap metadata.
        """
        if len(chunks) <= 1 or self._config.overlap_tokens <= 0:
            return OverlapResult(
                chunks=tuple(chunks),
                overlap_info=tuple({} for _ in chunks),
            )

        modified = []
        overlap_info = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk: no overlap
                modified.append(chunk)
                overlap_info.append({"is_first": True, "overlap_tokens": 0})
                continue

            # Add overlap from previous chunk
            prev_chunk = chunks[i - 1]
            overlap = self._extract_overlap(prev_chunk)

            if overlap:
                # Create new chunk with overlap prepended
                overlapped_text = overlap + "\n...\n" + chunk.text
                overlap_tokens_count = self._tokenizer.count_tokens(overlap)

                new_chunk = TextChunk.create(
                    text=overlapped_text,
                    token_count=chunk.token_count + overlap_tokens_count,
                    sequence_number=chunk.sequence_number,
                    char_start=chunk.char_start,
                    metadata={
                        **chunk.metadata,
                        "has_overlap": True,
                        "overlap_text": overlap,
                        "overlap_tokens": overlap_tokens_count,
                    },
                )
                modified.append(new_chunk)
                overlap_info.append(
                    {
                        "has_overlap": True,
                        "overlap_tokens": overlap_tokens_count,
                        "source_chunk": prev_chunk.sequence_number,
                    }
                )
            else:
                modified.append(chunk)
                overlap_info.append({"has_overlap": False})

        return OverlapResult(chunks=tuple(modified), overlap_info=tuple(overlap_info))

    def _extract_overlap(self, chunk: TextChunk) -> str:
        """Extract last N tokens from chunk for overlap."""
        if chunk.token_count <= self._config.overlap_tokens:
            return chunk.text

        tokens = self._tokenizer.encode_ordinary(chunk.text)
        overlap_tokens = tokens[-self._config.overlap_tokens :]
        return self._tokenizer.decode(overlap_tokens)

    def remove_overlap_for_processing(self, chunk: TextChunk) -> tuple[str, str]:
        """Extract core text and overlap from chunk for processing.

        Returns: (core_text, overlap_text)
        """
        if not chunk.metadata.get("has_overlap"):
            return chunk.text, ""

        overlap_text = chunk.metadata.get("overlap_text", "")
        core_text = chunk.text

        # Try to remove the overlap prefix
        if core_text.startswith(overlap_text + "\n...\n"):
            core_text = core_text[len(overlap_text) + 5 :]

        return core_text, overlap_text

    @staticmethod
    def merge_chunks(chunks: list[TextChunk]) -> str:
        """Merge chunks back into original text (best effort).

        Removes overlap markers and concatenates.
        """
        if not chunks:
            return ""

        parts = []
        for chunk in chunks:
            core, _ = OverlapHandler._extract_raw_text(chunk)
            parts.append(core)

        # Join with newlines (simple heuristic)
        return "\n".join(parts)

    @staticmethod
    def _extract_raw_text(chunk: TextChunk) -> tuple[str, str]:
        """Extract raw text without overlap markers."""
        if chunk.metadata.get("has_overlap"):
            overlap = chunk.metadata.get("overlap_text", "")
            text = chunk.text
            if text.startswith(overlap + "\n...\n"):
                return text[len(overlap) + 5 :], overlap
            return text, overlap
        return chunk.text, ""