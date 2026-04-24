"""Tests for translate_chapter.py using DIP-compliant GlossaryAwareTranslator."""
from unittest.mock import MagicMock

from pdftranslator.application.services.translation_service import TranslationResult
from pdftranslator.cli.commands.translate_chapter import (
    _get_language_for_split,
    _translate_chapter,
)
from pdftranslator.infrastructure.llm.base import BCP47Language


def test_translate_chapter_uses_glossary_aware_translator():
    chapter = MagicMock()
    chapter.original_text = "Hello world"
    chapter.id = 1
    chapter.chapter_number = 1

    mock_translator = MagicMock()
    mock_translator.translate.return_value = TranslationResult(
        original_chunks=1,
        translated_chunks=1,
        text="Hola mundo",
        errors=[],
    )

    mock_chapter_repo = MagicMock()
    mock_progress = MagicMock()
    mock_task_id = MagicMock()

    result = _translate_chapter(
        chapter=chapter,
        translator=mock_translator,
        source_lang="en",
        target_lang="es",
        chapter_repo=mock_chapter_repo,
        progress=mock_progress,
        task_id=mock_task_id,
    )

    assert result is True
    mock_translator.translate.assert_called_once()
    mock_chapter_repo.update.assert_called_once()


def test_get_language_for_split():
    assert _get_language_for_split("en") == BCP47Language.ENGLISH
    assert _get_language_for_split("ja") == BCP47Language.JAPANESE
    assert _get_language_for_split("es") == BCP47Language.SPANISH
    assert _get_language_for_split("unknown") == BCP47Language.ENGLISH
