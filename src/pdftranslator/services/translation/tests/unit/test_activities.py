"""
Unit tests for Translation Activities.

CUPID Principle: Unix Philosophy - Each test verifies one behavior.
"""

import pytest


class TestDetectLanguageActivity:
    """Tests for detect_language activity."""

    @pytest.mark.asyncio
    async def test_detect_english(self):
        """Test detecting English text."""
        from pdftranslator.services.translation.activities import detect_language_activity, DetectLanguageInput

        text = "This is a test sentence in English language."
        input_data = DetectLanguageInput(
            text=text,
            job_id=1,
            work_id=1,
        )
        result = await detect_language_activity(input_data)

        assert result.detected_lang == "en"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_detect_spanish(self):
        """Test detecting Spanish text."""
        from pdftranslator.services.translation.activities import detect_language_activity, DetectLanguageInput

        text = "Este es un texto en español para probar la detección."
        input_data = DetectLanguageInput(
            text=text,
            job_id=1,
            work_id=1,
        )
        result = await detect_language_activity(input_data)

        assert result.detected_lang == "es"

    @pytest.mark.asyncio
    async def test_text_stats_calculated(self):
        """Test that text statistics are calculated correctly."""
        from pdftranslator.services.translation.activities import detect_language_activity, DetectLanguageInput

        text = "Hello world. This is a test."
        input_data = DetectLanguageInput(
            text=text,
            job_id=1,
            work_id=1,
        )
        result = await detect_language_activity(input_data)

        assert result.text_stats["char_count"] == len(text)
        assert result.text_stats["word_count"] == len(text.split())
        assert result.text_stats["line_count"] == 1


class TestSegmentTextActivity:
    """Tests for segment_text activity."""

    @pytest.mark.asyncio
    async def test_segment_short_text(self):
        """Test segmenting short text that fits in one segment."""
        from pdftranslator.services.translation.activities import segment_text_activity, SegmentTextInput

        input_data = SegmentTextInput(
            text="This is a short text.",
            source_lang="en",
            target_lang="es",
            job_id=1,
            max_segment_length=1000,
        )
        result = await segment_text_activity(input_data)

        assert result.total_segments == 1
        assert result.total_chars == len("This is a short text.")
        assert result.segments[0]["source_text"] == "This is a short text."

    @pytest.mark.asyncio
    async def test_segment_long_text_multiple(self):
        """Test segmenting long text into multiple segments."""
        from pdftranslator.services.translation.activities import segment_text_activity, SegmentTextInput

        # Create text that will be split into multiple segments
        text = "Sentence one. " + "Sentence two. " * 50 + "Sentence three."
        input_data = SegmentTextInput(
            text=text,
            source_lang="en",
            target_lang="es",
            job_id=1,
            max_segment_length=100,
        )
        result = await segment_text_activity(input_data)

        assert result.total_segments > 1
        assert result.total_chars > 0
        # Verify segment numbers are sequential
        for i, segment in enumerate(result.segments):
            assert segment["segment_number"] == i + 1
            assert segment["target_text"] is None

    @pytest.mark.asyncio
    async def test_segment_empty_text(self):
        """Test segmenting empty text."""
        from pdftranslator.services.translation.activities import segment_text_activity, SegmentTextInput

        input_data = SegmentTextInput(
            text="",
            source_lang="en",
            target_lang="es",
            job_id=1,
        )
        result = await segment_text_activity(input_data)

        assert result.total_segments == 0
        assert result.total_chars == 0
        assert result.segments == []


class TestTranslateSegmentsActivity:
    """Tests for translate_segments activity."""

    @pytest.mark.asyncio
    async def test_translate_segments(self):
        """Test translating segments."""
        from pdftranslator.services.translation.activities import translate_segments_activity, TranslateSegmentsInput

        segments = [
            {"segment_number": 1, "source_text": "Hello world", "target_text": None},
            {"segment_number": 2, "source_text": "Good morning", "target_text": None},
        ]
        input_data = TranslateSegmentsInput(
            job_id=1,
            segments=segments,
            source_lang="en",
            target_lang="es",
            llm_provider="nvidia",
            model_name="meta/llama-3.1-70b-instruct",
        )
        result = await translate_segments_activity(input_data)

        assert result.translated_count == 2
        assert result.failed_count == 0
        assert len(result.errors) == 0
        assert len(result.segments) == 2
        assert all(s["target_text"] for s in result.segments)
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_translate_empty_segment_skipped(self):
        """Test that empty source text is skipped."""
        from pdftranslator.services.translation.activities import translate_segments_activity, TranslateSegmentsInput

        segments = [
            {"segment_number": 1, "source_text": "", "target_text": None},
        ]
        input_data = TranslateSegmentsInput(
            job_id=1,
            segments=segments,
            source_lang="en",
            target_lang="es",
            llm_provider="nvidia",
            model_name="meta/llama-3.1-70b-instruct",
        )
        result = await translate_segments_activity(input_data)

        # Empty segments are skipped (not returned in segments list)
        assert result.translated_count == 0
        assert result.failed_count == 0
        assert len(result.segments) == 0  # Empty segments filtered out


class TestQualityCheckActivity:
    """Tests for quality_check activity."""

    @pytest.mark.asyncio
    async def test_quality_check_passes(self):
        """Test quality check on good translations."""
        from pdftranslator.services.translation.activities import quality_check_activity, QualityCheckInput

        segments = [
            {"segment_number": 1, "source_text": "Hello world", "target_text": "Hola mundo"},
            {"segment_number": 2, "source_text": "Good morning", "target_text": "Buenos días"},
        ]
        input_data = QualityCheckInput(
            segments=segments,
            source_lang="en",
            target_lang="es",
            check_types=["completeness", "fluency"],
            threshold=0.7,
        )
        result = await quality_check_activity(input_data)

        assert result.checked_count == 2
        assert result.passed_count == 2
        assert result.failed_count == 0
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_quality_check_fails_empty(self):
        """Test quality check fails on empty translation."""
        from pdftranslator.services.translation.activities import quality_check_activity, QualityCheckInput

        segments = [
            {"segment_number": 1, "source_text": "Hello world", "target_text": ""},
        ]
        input_data = QualityCheckInput(
            segments=segments,
            source_lang="en",
            target_lang="es",
            check_types=["completeness"],
            threshold=0.7,
        )
        result = await quality_check_activity(input_data)

        assert result.checked_count == 1
        assert result.passed_count == 0
        assert result.failed_count == 1
        assert len(result.issues) == 1
        assert result.issues[0]["check_type"] == "completeness"


class TestStoreTranslationsActivity:
    """Tests for store_translations activity."""

    @pytest.mark.asyncio
    async def test_store_translations(self):
        """Test storing translations."""
        from pdftranslator.services.translation.activities import store_translations_activity, StoreTranslationsInput

        segments = [
            {"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "translated": True},
            {"segment_number": 2, "source_text": "World", "target_text": "Mundo", "translated": True},
        ]
        input_data = StoreTranslationsInput(
            job_id=1,
            segments=segments,
            pipeline_id="test-pipeline-id",
        )
        result = await store_translations_activity(input_data)

        assert result.stored_count == 2
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_store_untranslated_segment(self):
        """Test storing skips untranslated segments."""
        from pdftranslator.services.translation.activities import store_translations_activity, StoreTranslationsInput

        segments = [
            {"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "translated": True},
            {"segment_number": 2, "source_text": "World", "target_text": None, "translated": False},
        ]
        input_data = StoreTranslationsInput(
            job_id=1,
            segments=segments,
            pipeline_id="test-pipeline-id",
        )
        result = await store_translations_activity(input_data)

        assert result.stored_count == 1
        assert len(result.errors) == 1


class TestGenerateAudioActivity:
    """Tests for generate_audio activity."""

    @pytest.mark.asyncio
    async def test_generate_audio_no_text(self):
        """Test generating audio with no translated text."""
        from pdftranslator.services.translation.activities import generate_audio_activity, GenerateAudioInput

        segments = [
            {"segment_number": 1, "source_text": "Hello", "target_text": "", "translated": False},
        ]
        input_data = GenerateAudioInput(
            job_id=1,
            segments=segments,
            target_lang="es",
        )
        result = await generate_audio_activity(input_data)

        # Should return error when no translated text
        assert result.audio_file_path is None
        assert result.duration_ms == 0
        assert len(result.errors) == 1
        assert "No translated text" in result.errors[0]

    @pytest.mark.asyncio
    async def test_generate_audio_with_text(self):
        """Test generating audio with translated text (mocked subprocess)."""
        from pdftranslator.services.translation.activities import generate_audio_activity, GenerateAudioInput
        from unittest.mock import patch, AsyncMock

        segments = [
            {"segment_number": 1, "source_text": "Hello", "target_text": "Hola", "translated": True},
            {"segment_number": 2, "source_text": "World", "target_text": "Mundo", "translated": True},
        ]
        input_data = GenerateAudioInput(
            job_id=1,
            segments=segments,
            target_lang="es",
            voice="Samantha",
            format="m4a",
        )

        # Mock the subprocess call
        mock_audio_data = b"fake audio data"
        with patch("pdftranslator.services.translation.activities.generate_audio.asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(mock_audio_data, b""))
            mock_subprocess.return_value = mock_proc

            with patch("pdftranslator.services.translation.activities.generate_audio.Path.write_bytes"):
                result = await generate_audio_activity(input_data)

        assert result.audio_file_path is not None
        assert result.duration_ms >= 0
        assert result.total_chars > 0
        assert len(result.errors) == 0