"""MlxAudioSynthesizer — implements AudioSynthesizer protocol using MLX TTS.

Resolves OCP-4: New TTS backend added without modifying existing code.
Uses Apple MLX framework for on-device TTS on Apple Silicon.
"""
from __future__ import annotations

import logging
from pathlib import Path

from pdftranslator.infrastructure.audio.ffmpeg_merger import merge_audio_files

logger = logging.getLogger(__name__)


class MlxAudioSynthesizer:
    """MLX-based TTS synthesizer for Apple Silicon.

    Uses the mlx-audio package for on-device text-to-speech.
    Falls back gracefully if mlx-audio is not installed.
    """

    def __init__(self, model_name: str = "mlx-community/TTS", settings=None):
        self._model_name = model_name
        self._settings = settings
        self._pipeline = None

    @property
    def is_available(self) -> bool:
        try:
            import mlx_audio  # noqa: F401

            return True
        except ImportError:
            logger.debug("mlx-audio not installed, MlxAudioSynthesizer unavailable")
            return False

    @property
    def name(self) -> str:
        return "mlx"

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

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if self._pipeline is None:
                from mlx_audio.tts import Pipeline

                self._pipeline = Pipeline(self._model_name)

            audio = self._pipeline.generate(text, voice=voice, speed=speed, lang=language)

            import soundfile as sf

            sf.write(str(output_path), audio.samples, audio.sr)
            logger.info(f"MLX audio saved: {output_path}")
            return True

        except ImportError:
            logger.error(
                "mlx-audio package not installed. Install with: pip install mlx-audio"
            )
            return False
        except Exception as e:
            logger.error(f"Error in MLX TTS synthesis: {e}", exc_info=True)
            return False

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
