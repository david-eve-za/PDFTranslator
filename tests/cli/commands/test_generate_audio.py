"""Tests for generate-audio CLI command."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_pool():
    return MagicMock()


class TestGenerateAudioCommand:
    """Tests for generate_audio command."""

    def test_command_imports(self):
        """Test that the command can be imported."""
        from pdftranslator.cli.commands.generate_audio import generate_audio

        assert callable(generate_audio)

    def test_generate_chapter_audio_success(self, mock_pool, tmp_path):
        """Test successful audio generation for a single chapter."""
        from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
        from pdftranslator.core.models.work import Chapter, Volume, Work
        from pdftranslator.core.config.settings import Settings

        chapter = Chapter(
            id=1,
            volume_id=1,
            chapter_number=3,
            translated_text="This is translated text.",
        )
        volume = Volume(id=1, work_id=1, volume_number=1)
        work = Work(id=1, title="TestWork")

        with patch(
            "pdftranslator.cli.commands.generate_audio.AudioGenerator"
        ) as mock_audio_gen:
            mock_audio_gen.return_value.process_texts.return_value = True

            settings = Settings.get()
            result = _generate_chapter_audio(chapter, volume, work, settings)

            assert result is True
            mock_audio_gen.return_value.process_texts.assert_called_once()

    def test_generate_chapter_audio_no_translation(self, mock_pool):
        """Test audio generation when chapter has no translated text."""
        from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
        from pdftranslator.core.models.work import Chapter, Volume, Work
        from pdftranslator.core.config.settings import Settings

        chapter = Chapter(id=1, volume_id=1, chapter_number=1, translated_text=None)
        volume = Volume(id=1, work_id=1, volume_number=1)
        work = Work(id=1, title="TestWork")

        settings = Settings.get()
        result = _generate_chapter_audio(chapter, volume, work, settings)

        assert result is False

    def test_generate_chapter_audio_already_exists(self, mock_pool, tmp_path):
        """Test audio generation when file already exists."""
        from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
        from pdftranslator.core.models.work import Chapter, Volume, Work
        from pdftranslator.core.config.settings import Settings

        chapter = Chapter(
            id=1, volume_id=1, chapter_number=1, translated_text="Translated text"
        )
        volume = Volume(id=1, work_id=1, volume_number=1)
        work = Work(id=1, title="TestWork")

        settings = Settings.get()
        work_title = work.title.replace(" ", "_")
        output_path = (
            settings.paths.audiobooks_dir
            / work_title
            / f"Vol{volume.volume_number}"
            / f"{work_title}_Vol{volume.volume_number}_Ch{chapter.chapter_number:03d}.m4a"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("existing audio")

        result = _generate_chapter_audio(chapter, volume, work, settings)

        assert result is True

    def test_generate_volume_audio(self, mock_pool):
        """Test audio generation for all chapters in a volume."""
        from pdftranslator.cli.commands.generate_audio import _generate_volume_audio
        from pdftranslator.core.models.work import Chapter, Volume, Work
        from pdftranslator.core.config.settings import Settings

        chapters = [
            Chapter(id=1, volume_id=1, chapter_number=1, translated_text="Chapter 1"),
            Chapter(id=2, volume_id=1, chapter_number=2, translated_text="Chapter 2"),
        ]
        volume = Volume(id=1, work_id=1, volume_number=1)
        work = Work(id=1, title="TestWork")

        mock_chapter_repo = MagicMock()
        mock_chapter_repo.get_by_volume.return_value = chapters

        with patch(
            "pdftranslator.cli.commands.generate_audio._generate_chapter_audio"
        ) as mock_gen:
            mock_gen.return_value = True

            settings = Settings.get()
            success, skip, fail = _generate_volume_audio(
                volume, work, settings, mock_chapter_repo
            )

            assert success == 2
            assert skip == 0
            assert fail == 0

    def test_format_chapter_display(self):
        """Test chapter display formatting."""
        from pdftranslator.cli.commands.generate_audio import _format_chapter_display
        from pdftranslator.core.models.work import Chapter

        chapter_numbered = Chapter(id=1, chapter_number=5, title="The Beginning")
        assert "Chapter 5" in _format_chapter_display(chapter_numbered)

        chapter_prologue = Chapter(id=2, chapter_number=None, title="Prologue")
        assert "Prologue" in _format_chapter_display(chapter_prologue)

    def test_get_chapter_sort_key(self):
        """Test chapter sorting."""
        from pdftranslator.cli.commands.generate_audio import _get_chapter_sort_key
        from pdftranslator.core.models.work import Chapter

        prologue = Chapter(id=1, chapter_number=None, title="Prologue")
        chapter1 = Chapter(id=2, chapter_number=1)
        chapter2 = Chapter(id=3, chapter_number=2)
        epilogue = Chapter(id=4, chapter_number=None, title="Epilogue")

        chapters = [chapter2, epilogue, chapter1, prologue]
        sorted_chapters = sorted(chapters, key=_get_chapter_sort_key)

        assert sorted_chapters[0].title == "Prologue"
        assert sorted_chapters[1].chapter_number == 1
        assert sorted_chapters[2].chapter_number == 2
        assert sorted_chapters[3].title == "Epilogue"
