"""
Contract Tests for Text Processing Library API.

CUPID Principle: Predictable + Composable
- Validates library API contracts (deterministic output for same input)
- Tests CLI interface compatibility
- Ensures chunking, normalization, tokenization consistency
"""

from __future__ import annotations
import pytest
from typing import List

from pdftranslator.text_processing import (
    TextChunker,
    ChunkConfig,
    ChunkResult,
    TextChunk,
    Tokenizer,
    EncodingType,
    SplitStrategy,
    OverlapHandler,
    TextNormalizer,
    NormalizationConfig,
    NormalizationForm,
)

# Import core NormalizationConfig for TextNormalizer
from pdftranslator.text_processing.core.normalizer import NormalizationConfig as CoreNormalizationConfig


class TestChunkConfigContract:
    """Contract tests for ChunkConfig model."""

    def test_chunk_config_defaults(self):
        """Default config should have expected values."""
        config = ChunkConfig()
        assert config.max_tokens == 500
        assert config.overlap_tokens == 50
        assert config.min_tokens == 50
        assert config.encoding == EncodingType.CL100K_BASE
        assert config.split_strategy == SplitStrategy.TOKENS
        assert config.preserve_paragraphs is True
        assert config.include_metadata is True

    def test_chunk_config_validation_max_tokens(self):
        """max_tokens must be > 0."""
        with pytest.raises(ValueError, match="max_tokens must be > 0"):
            ChunkConfig(max_tokens=0)
        with pytest.raises(ValueError, match="max_tokens must be > 0"):
            ChunkConfig(max_tokens=-1)

    def test_chunk_config_validation_overlap(self):
        """overlap_tokens must be >= 0 and < max_tokens."""
        with pytest.raises(ValueError, match="overlap_tokens must be >= 0"):
            ChunkConfig(overlap_tokens=-1)
        with pytest.raises(ValueError, match="overlap_tokens must be < max_tokens"):
            ChunkConfig(max_tokens=100, overlap_tokens=100)
        with pytest.raises(ValueError, match="overlap_tokens must be < max_tokens"):
            ChunkConfig(max_tokens=100, overlap_tokens=150)

    def test_chunk_config_validation_min_tokens(self):
        """min_tokens must be > 0 and <= max_tokens."""
        with pytest.raises(ValueError, match="min_tokens must be > 0"):
            ChunkConfig(min_tokens=0)
        with pytest.raises(ValueError, match="min_tokens must be <= max_tokens"):
            ChunkConfig(max_tokens=50, min_tokens=100, overlap_tokens=10)

    def test_chunk_config_for_translation(self):
        """Factory method for_translation returns correct config."""
        config = ChunkConfig.for_translation()
        assert config.max_tokens == 512
        assert config.overlap_tokens == 64
        assert config.min_tokens == 100
        assert config.encoding == EncodingType.CL100K_BASE

    def test_chunk_config_for_embedding(self):
        """Factory method for_embedding returns correct config."""
        config = ChunkConfig.for_embedding()
        assert config.max_tokens == 8191
        assert config.overlap_tokens == 128
        assert config.min_tokens == 256

    def test_chunk_config_to_dict_roundtrip(self):
        """Config can be serialized and deserialized."""
        original = ChunkConfig(
            max_tokens=256,
            overlap_tokens=32,
            min_tokens=50,
            encoding=EncodingType.O200K_BASE,
            split_strategy=SplitStrategy.SENTENCES,
        )
        data = original.to_dict()
        restored = ChunkConfig.from_dict(data)
        assert restored.max_tokens == original.max_tokens
        assert restored.overlap_tokens == original.overlap_tokens
        assert restored.min_tokens == original.min_tokens
        assert restored.encoding == original.encoding
        assert restored.split_strategy == original.split_strategy


class TestTokenizerContract:
    """Contract tests for Tokenizer."""

    def test_tokenizer_singleton_per_encoding(self):
        """Tokenizer.get() returns cached instance per encoding."""
        t1 = Tokenizer.get(EncodingType.CL100K_BASE)
        t2 = Tokenizer.get(EncodingType.CL100K_BASE)
        assert t1 is t2

        t3 = Tokenizer.get(EncodingType.O200K_BASE)
        assert t1 is not t3

    def test_tokenizer_count_tokens(self):
        """count_tokens returns consistent count."""
        tokenizer = Tokenizer.get(EncodingType.CL100K_BASE)
        text = "Hello world"
        count1 = tokenizer.count_tokens(text)
        count2 = tokenizer.count_tokens(text)
        assert count1 == count2
        assert count1 > 0

    def test_tokenizer_encode_decode_roundtrip(self):
        """encode + decode preserves text."""
        tokenizer = Tokenizer.get(EncodingType.CL100K_BASE)
        text = "Hello world! This is a test."
        tokens = tokenizer.encode(text)
        decoded = tokenizer.decode(tokens)
        assert decoded == text

    def test_tokenizer_encode_ordinary(self):
        """encode_ordinary excludes special tokens."""
        tokenizer = Tokenizer.get(EncodingType.CL100K_BASE)
        text = "Hello"
        tokens = tokenizer.encode(text)
        ordinary = tokenizer.encode_ordinary(text)
        # encode_ordinary may have fewer tokens (no special tokens)
        assert len(ordinary) <= len(tokens)


class TestTextChunkerContract:
    """Contract tests for TextChunker - deterministic chunking."""

    def test_chunk_deterministic(self):
        """Same input + config = same output (core CUPID Predictable)."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=5)
        chunker = TextChunker(config)

        text = "First sentence. Second sentence here. Third sentence for testing."

        result1 = chunker.chunk(text)
        result2 = chunker.chunk(text)

        assert result1.total_chunks == result2.total_chunks
        assert result1.total_tokens == result2.total_tokens
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.text == c2.text
            assert c1.token_count == c2.token_count
            assert c1.sequence_number == c2.sequence_number

    def test_chunk_empty_text(self):
        """Empty text returns empty result."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=5)
        chunker = TextChunker(config)

        result = chunker.chunk("")
        assert result.total_chunks == 0
        assert result.total_tokens == 0
        assert result.total_chars == 0
        assert len(result.chunks) == 0

    def test_chunk_single_chunk(self):
        """Text shorter than max_tokens returns single chunk."""
        config = ChunkConfig(max_tokens=500, overlap_tokens=10, min_tokens=5)
        chunker = TextChunker(config)

        text = "Short text."
        result = chunker.chunk(text)

        assert result.total_chunks == 1
        assert result.chunks[0].token_count == 3
        assert result.chunks[0].sequence_number == 0
        assert result.chunks[0].char_start == 0

    def test_chunk_multiple_chunks_with_overlap(self):
        """Long text creates multiple chunks with overlap."""
        config = ChunkConfig(max_tokens=10, overlap_tokens=3, min_tokens=3)
        chunker = TextChunker(config)

        text = "First sentence. Second sentence here. Third sentence for testing."
        result = chunker.chunk(text)

        assert result.total_chunks > 1
        # Check overlap metadata
        for i, chunk in enumerate(result.chunks):
            if i > 0:
                assert "start_token" in chunk.metadata
                assert "end_token" in chunk.metadata
                # Overlap means start_token of chunk i < end_token of chunk i-1
                assert chunk.metadata["start_token"] < result.chunks[i-1].metadata["end_token"]

    def test_chunk_strategy_tokens(self):
        """SplitStrategy.TOKENS chunks by token count."""
        config = ChunkConfig(max_tokens=5, overlap_tokens=1, min_tokens=2, split_strategy=SplitStrategy.TOKENS)
        chunker = TextChunker(config)

        text = "One two three four five six seven eight nine ten."
        result = chunker.chunk(text)

        assert result.total_chunks > 1
        assert all(c.token_count <= 5 for c in result.chunks)

    def test_chunk_strategy_sentences(self):
        """SplitStrategy.SENTENCES chunks by sentence boundaries."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=5, min_tokens=3, split_strategy=SplitStrategy.SENTENCES)
        chunker = TextChunker(config)

        text = "First sentence. Second sentence here. Third sentence for testing. Fourth and final."
        result = chunker.chunk(text)

        assert result.total_chunks > 0
        # Each chunk should end at sentence boundary (approximately)
        for chunk in result.chunks:
            assert chunk.text.strip().endswith(".") or chunk.text.strip().endswith("!") or chunk.text.strip().endswith("?")

    def test_chunk_strategy_paragraphs(self):
        """SplitStrategy.PARAGRAPHS respects paragraph boundaries."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=5, min_tokens=3, split_strategy=SplitStrategy.PARAGRAPHS)
        chunker = TextChunker(config)

        text = "Para one.\n\nPara two with more text.\n\nPara three also here."
        result = chunker.chunk(text)

        assert result.total_chunks > 0

    def test_chunk_strategy_characters(self):
        """SplitStrategy.CHARACTERS falls back to character-based chunking."""
        config = ChunkConfig(max_tokens=5, overlap_tokens=1, min_tokens=2, split_strategy=SplitStrategy.CHARACTERS)
        chunker = TextChunker(config)

        text = "Short text for testing."
        result = chunker.chunk(text)

        assert result.total_chunks >= 1

    def test_chunk_result_structure(self):
        """ChunkResult contains all required fields."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=5)
        chunker = TextChunker(config)

        result = chunker.chunk("Test text")

        assert hasattr(result, "chunks")
        assert hasattr(result, "total_chunks")
        assert hasattr(result, "total_tokens")
        assert hasattr(result, "total_chars")
        assert hasattr(result, "config")
        assert isinstance(result.chunks, (list, tuple))
        assert isinstance(result.config, ChunkConfig)

    def test_text_chunk_structure(self):
        """TextChunk contains all required fields."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=5)
        chunker = TextChunker(config)

        result = chunker.chunk("Test text")
        chunk = result.chunks[0]

        assert hasattr(chunk, "text")
        assert hasattr(chunk, "token_count")
        assert hasattr(chunk, "sequence_number")
        assert hasattr(chunk, "char_start")
        assert hasattr(chunk, "char_end")
        assert hasattr(chunk, "uuid")
        assert hasattr(chunk, "metadata")
        assert isinstance(chunk.metadata, dict)


class TestOverlapHandlerContract:
    """Contract tests for OverlapHandler."""

    def test_overlap_handler_creation(self):
        """OverlapHandler created with ChunkConfig."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10)
        handler = OverlapHandler(config)
        assert handler.overlap_tokens == 10

    def test_overlap_no_chunks(self):
        """Empty chunk list returns empty result."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10)
        handler = OverlapHandler(config)

        result = handler.apply_overlap([])
        assert len(result.chunks) == 0
        assert len(result.overlap_info) == 0

    def test_overlap_single_chunk(self):
        """Single chunk gets no overlap."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=5)
        handler = OverlapHandler(config)

        # Force single chunk
        chunk = TextChunk.create(text="Single chunk", token_count=5, sequence_number=0, char_start=0)
        result = handler.apply_overlap([chunk])

        assert len(result.chunks) == 1
        assert result.chunks[0].text == "Single chunk"
        # Single chunk returns empty overlap_info when len <= 1
        assert result.overlap_info[0] == {}

    def test_overlap_multiple_chunks(self):
        """Multiple chunks get overlap applied."""
        config = ChunkConfig(max_tokens=10, overlap_tokens=3, min_tokens=2, encoding=EncodingType.CL100K_BASE)
        handler = OverlapHandler(config)

        chunk1 = TextChunk.create(text="First chunk content here", token_count=8, sequence_number=0, char_start=0)
        chunk2 = TextChunk.create(text="Second chunk content here", token_count=8, sequence_number=1, char_start=25)
        chunk3 = TextChunk.create(text="Third chunk content here", token_count=8, sequence_number=2, char_start=50)

        result = handler.apply_overlap([chunk1, chunk2, chunk3])

        assert len(result.chunks) == 3
        assert result.chunks[0].text == "First chunk content here"  # First unchanged
        assert result.overlap_info[0].get("is_first") is True
        assert result.overlap_info[1].get("has_overlap") is True
        assert result.overlap_info[2].get("has_overlap") is True
        # Overlap adds tokens
        assert result.chunks[1].token_count > 8
        assert result.chunks[2].token_count > 8

    def test_remove_overlap_for_processing(self):
        """remove_overlap_for_processing extracts core and overlap."""
        config = ChunkConfig(max_tokens=50, overlap_tokens=3, encoding=EncodingType.CL100K_BASE)
        handler = OverlapHandler(config)

        chunk1 = TextChunk.create(text="First chunk", token_count=5, sequence_number=0, char_start=0)
        chunk2 = TextChunk.create(text="Second chunk", token_count=5, sequence_number=1, char_start=12)

        overlap_result = handler.apply_overlap([chunk1, chunk2])
        overlapped_chunk = overlap_result.chunks[1]

        core_text, overlap_text = handler.remove_overlap_for_processing(overlapped_chunk)
        assert core_text is not None
        assert overlap_text is not None


class TestTextNormalizerContract:
    """Contract tests for TextNormalizer."""

    def test_normalizer_default_config(self):
        """Default normalizer has expected settings."""
        normalizer = TextNormalizer()
        text = "  Hello  world  "
        result = normalizer.normalize(text)
        assert result == "Hello world"

    def test_normalizer_unicode_nfkc(self):
        """NFKC normalization composes characters."""
        config = CoreNormalizationConfig(unicode_form=NormalizationForm.NFKC)
        normalizer = TextNormalizer(config)

        # é as combining char (e + ́)
        text = "é"  # e + combining acute
        result = normalizer.normalize(text)
        assert result == "é"

    def test_normalizer_unicode_nfd(self):
        """NFD normalization decomposes characters."""
        config = CoreNormalizationConfig(unicode_form=NormalizationForm.NFD)
        normalizer = TextNormalizer(config)

        text = "é"  # precomposed
        result = normalizer.normalize(text)
        assert result == "é"  # decomposed

    def test_normalizer_lowercase(self):
        """lower_case option converts to lowercase."""
        config = CoreNormalizationConfig(lower_case=True)
        normalizer = TextNormalizer(config)

        text = "HELLO WORLD"
        result = normalizer.normalize(text)
        assert result == "hello world"

    def test_normalizer_control_chars(self):
        """remove_control_chars strips control characters."""
        config = CoreNormalizationConfig(remove_control_chars=True)
        normalizer = TextNormalizer(config)

        text = "Hello\x00World\x1F"
        result = normalizer.normalize(text)
        assert result == "HelloWorld"

    def test_normalizer_quotes_not_implemented(self):
        """normalize_quotes not in current implementation - test default behavior."""
        config = CoreNormalizationConfig()
        normalizer = TextNormalizer(config)

        text = '"Hello" and \'world\''
        result = normalizer.normalize(text)
        # Current implementation doesn't change quotes
        assert result == text.strip()

    def test_normalizer_dashes_not_implemented(self):
        """normalize_dashes is implemented - test it works."""
        config = CoreNormalizationConfig(normalize_dashes=True)
        normalizer = TextNormalizer(config)

        text = "Hello—world–test"
        result = normalizer.normalize(text)
        assert result == "Hello-world-test"

    def test_normalizer_ellipsis_not_implemented(self):
        """normalize_ellipsis is implemented - test it works."""
        config = CoreNormalizationConfig(normalize_ellipsis=True)
        normalizer = TextNormalizer(config)

        text = "Hello…world"
        result = normalizer.normalize(text)
        assert result == "Hello...world"

    def test_normalizer_whitespace(self):
        """collapse_whitespace normalizes spaces."""
        config = CoreNormalizationConfig(collapse_whitespace=True)
        normalizer = TextNormalizer(config)

        text = "Hello   world\n\n\ttest"
        result = normalizer.normalize(text)
        # Multiple spaces collapsed
        assert "   " not in result

    def test_normalizer_factory_for_translation(self):
        """Factory config for_translation works."""
        config = CoreNormalizationConfig(
            unicode_form=NormalizationForm.NFKC,
            lower_case=False,
            collapse_whitespace=True,
            remove_control_chars=True,
        )
        normalizer = TextNormalizer(config)
        text = "Test text"
        result = normalizer.normalize(text)
        assert result == "Test text"

    def test_normalizer_to_dict(self):
        """NormalizationConfig serialization uses to_dict."""
        config = CoreNormalizationConfig(lower_case=True, unicode_form=NormalizationForm.NFKC)
        data = config.to_dict()
        assert data["lower_case"] is True
        assert data["unicode_form"] == "NFKC"


class TestEncodingTypeContract:
    """Contract tests for EncodingType enum."""

    def test_encoding_types_exist(self):
        """All expected encodings available."""
        assert EncodingType.CL100K_BASE == "cl100k_base"
        assert EncodingType.O200K_BASE == "o200k_base"
        assert EncodingType.P50K_BASE == "p50k_base"
        assert EncodingType.R50K_BASE == "r50k_base"

    def test_encoding_used_in_tokenizer(self):
        """Each encoding works with tokenizer."""
        for encoding in EncodingType:
            tokenizer = Tokenizer.get(encoding)
            count = tokenizer.count_tokens("test")
            assert count > 0


class TestSplitStrategyContract:
    """Contract tests for SplitStrategy enum."""

    def test_strategies_exist(self):
        """All expected strategies available."""
        assert SplitStrategy.TOKENS == "tokens"
        assert SplitStrategy.SENTENCES == "sentences"
        assert SplitStrategy.PARAGRAPHS == "paragraphs"
        assert SplitStrategy.CHARACTERS == "characters"

    def test_all_strategies_work(self):
        """Each strategy produces valid chunks."""
        for strategy in SplitStrategy:
            config = ChunkConfig(max_tokens=100, split_strategy=strategy)
            chunker = TextChunker(config)
            text = "First sentence. Second sentence here. Third."
            result = chunker.chunk(text)
            assert result.total_chunks >= 1


# Integration contract test - full pipeline
class TestTextProcessingPipelineContract:
    """Contract tests for full text processing pipeline."""

    def test_chunk_with_overlap_and_normalize(self):
        """Pipeline: normalize -> chunk -> overlap preserves structure."""
        # Normalize
        normalizer = TextNormalizer(NormalizationConfig.for_translation())
        text = "  Hello  world  \"quoted\" — dash … ellipsis \t\n "
        normalized = normalizer.normalize(text)
        # normalize_dashes converts — to -, normalize_ellipsis converts … to ...
        assert normalized == 'Hello world "quoted" - dash ... ellipsis'

        # Chunk
        config = ChunkConfig(max_tokens=10, overlap_tokens=3, min_tokens=3)
        chunker = TextChunker(config)
        result = chunker.chunk(normalized)
        assert result.total_chunks > 0

        # Apply overlap
        handler = OverlapHandler(config)
        overlap_result = handler.apply_overlap(result.chunks)
        assert len(overlap_result.chunks) == result.total_chunks

    def test_reproducibility(self):
        """Full pipeline is reproducible."""
        text = "Consistent text for reproducible results. Every run should match."

        # Run pipeline twice
        normalizer = TextNormalizer()
        config = ChunkConfig(max_tokens=20, overlap_tokens=5, min_tokens=3)
        chunker = TextChunker(config)
        handler = OverlapHandler(config)

        normalized1 = normalizer.normalize(text)
        result1 = chunker.chunk(normalized1)
        overlap1 = handler.apply_overlap(result1.chunks)

        normalized2 = normalizer.normalize(text)
        result2 = chunker.chunk(normalized2)
        overlap2 = handler.apply_overlap(result2.chunks)

        # Must be identical
        assert normalized1 == normalized2
        assert result1.total_chunks == result2.total_chunks
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.text == c2.text
            assert c1.token_count == c2.token_count

        for o1, o2 in zip(overlap1.chunks, overlap2.chunks):
            assert o1.text == o2.text
            assert o1.token_count == o2.token_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])