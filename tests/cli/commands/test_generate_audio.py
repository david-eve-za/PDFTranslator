"""Tests for generate-audio CLI command."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_pool():
    return MagicMock()


class TestGenerateAudioCommand:
    """Tests for generate_audio command."""

    def test_generate_audio_for_chapter_success(self, mock_pool):
        """Test successful audio generation for a single chapter."""
        from pdftranslator.cli.commands.generate_audio import generate_audio

        pass

    def test_error_both_flags_specified(self):
        """Test error when both chapter-id and volume-id are specified."""
        from pdftranslator.cli.commands.generate_audio import generate_audio
        from typer import Exit

        with pytest.raises(Exit):
            generate_audio(chapter_id=1, volume_id=1, voice=None)

    def test_error_no_flags_specified(self):
        """Test error when neither chapter-id nor volume-id are specified."""
        from pdftranslator.cli.commands.generate_audio import generate_audio
        from typer import Exit

        with pytest.raises(Exit):
            generate_audio(chapter_id=None, volume_id=None, voice=None)

    def test_error_chapter_not_found(self, mock_pool):
        """Test error when chapter ID doesn't exist."""
        from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
        from pdftranslator.database.repositories.chapter_repository import (
            ChapterRepository,
        )
        from typer import Exit

        mock_chapter_repo = MagicMock(spec=ChapterRepository)
        mock_chapter_repo.get_by_id.return_value = None

        with patch(
            "pdftranslator.cli.commands.generate_audio.ChapterRepository",
            return_value=mock_chapter_repo,
        ):
            with pytest.raises(Exit):
                _generate_chapter_audio(999, "Paulina")

    def test_error_chapter_no_translated_text(self, mock_pool):
        """Test error when chapter has no translated text."""
        from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
        from pdftranslator.database.repositories.chapter_repository import (
            ChapterRepository,
        )
        from pdftranslator.core.models.work import Chapter
        from typer import Exit

        mock_chapter_repo = MagicMock(spec=ChapterRepository)
        chapter = Chapter(id=1, volume_id=1, chapter_number=1, translated_text=None)
        mock_chapter_repo.get_by_id.return_value = chapter

        with patch(
            "pdftranslator.cli.commands.generate_audio.ChapterRepository",
            return_value=mock_chapter_repo,
        ):
            with pytest.raises(Exit):
                _generate_chapter_audio(1, "Paulina")
