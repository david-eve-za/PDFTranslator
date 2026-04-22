"""MacSaySynthesizer — implements AudioSynthesizer protocol.

Resolves OCP-4 and SRP-7: TTS backend extracted from AudioGenerator.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer

logger = logging.getLogger(__name__)


class MacSaySynthesizer:
    """macOS 'say' command TTS synthesizer."""

    _TEXT_NORMALIZATION_MAP = {
        "\u201d": '"',
        "\u201c": '"',
        "\u2019": "'",
        "\u2018": "'",
        "\u2014": "-",
        "\u2013": "-",
        "\u2026": "...",
        "<br>": "\n",
    }

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.get()
        self._voice = self._settings.processing.voice

    @property
    def is_available(self) -> bool:
        return shutil.which("say") is not None

    @property
    def name(self) -> str:
        return "mac_say"

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "es",
    ) -> bool:
        if not text or not text.strip():
            logger.warning("Input text is empty. Skipping audio generation.")
            return False

        voice_to_use = voice if voice != "default" else self._voice
        normalized_text = self._normalize_text(text)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temp_text_file = output_path.with_suffix(".txt")
            with open(temp_text_file, "w", encoding="utf-8") as f:
                f.write(normalized_text)

            subprocess.run(
                ["say", "-v", voice_to_use, "-o", str(output_path), "-f", str(temp_text_file)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Audio chunk saved: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during text-to-audio conversion: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in synthesize: {e}", exc_info=True)
            return False
        finally:
            if temp_text_file.exists():
                temp_text_file.unlink()

    def merge_audio(
        self,
        audio_files: list[Path],
        output_path: Path,
    ) -> bool:
        if not audio_files:
            return False
        try:
            return merge_audio_files(audio_files, output_path)
        except Exception as e:
            logger.error(f"Error merging audio files: {e}", exc_info=True)
            return False

    def _normalize_text(self, text: str) -> str:
        normalized = text
        for old, new in self._TEXT_NORMALIZATION_MAP.items():
            normalized = normalized.replace(old, new)
        return normalized
