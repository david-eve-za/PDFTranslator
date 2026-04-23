"""AudioSynthesizerFactory — creates AudioSynthesizer instances by engine type.

Resolves OCP-4: New TTS engines can be added without modifying consumers.
"""
from __future__ import annotations

import logging

from pdftranslator.core.config.processing import TTSEngine
from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer

logger = logging.getLogger(__name__)


class AudioSynthesizerFactory:
    """Factory for creating AudioSynthesizer instances based on engine type."""

    _REGISTRY: dict[TTSEngine, type] = {}

    @classmethod
    def register(cls, engine: TTSEngine, synthesizer_class: type) -> None:
        cls._REGISTRY[engine] = synthesizer_class

    @classmethod
    def create(
        cls,
        engine: TTSEngine | None = None,
        settings: Settings | None = None,
    ) -> AudioSynthesizer:
        settings = settings or Settings.get()
        engine = engine or settings.processing.tts_engine

        if engine in cls._REGISTRY:
            synthesizer_class = cls._REGISTRY[engine]
        elif engine == TTSEngine.MAC_SAY:
            from pdftranslator.infrastructure.audio.mac_say_synthesizer import (
                MacSaySynthesizer,
            )

            synthesizer_class = MacSaySynthesizer
        elif engine == TTSEngine.MLX:
            from pdftranslator.infrastructure.audio.mlx_audio_synthesizer import (
                MlxAudioSynthesizer,
            )

            synthesizer_class = MlxAudioSynthesizer
        elif engine == TTSEngine.FISH_SPEECH:
            from pdftranslator.infrastructure.audio.fish_speech_synthesizer import (
                FishSpeechSynthesizer,
            )

            synthesizer_class = FishSpeechSynthesizer
        else:
            raise ValueError(f"Unknown TTS engine: {engine}")

        instance = synthesizer_class(settings=settings)

        if not instance.is_available:
            logger.warning(
                f"TTS engine '{instance.name}' is not available. "
                f"Falling back to mac_say."
            )
            from pdftranslator.infrastructure.audio.mac_say_synthesizer import (
                MacSaySynthesizer,
            )

            instance = MacSaySynthesizer(settings=settings)

        return instance
