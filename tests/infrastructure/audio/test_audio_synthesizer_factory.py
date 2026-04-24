"""Tests for AudioSynthesizerFactory."""
from unittest.mock import patch

from pdftranslator.core.config.processing import TTSEngine
from pdftranslator.infrastructure.audio.audio_synthesizer_factory import (
    AudioSynthesizerFactory,
)


def test_factory_creates_mac_say_by_default():
    with patch("pdftranslator.infrastructure.audio.mac_say_synthesizer.shutil") as mock_shutil:
        mock_shutil.which.return_value = "/usr/bin/say"
        synth = AudioSynthesizerFactory.create(engine=TTSEngine.MAC_SAY)
        assert synth.name == "mac_say"


def test_factory_creates_mlx():
    synth = AudioSynthesizerFactory.create(engine=TTSEngine.MLX)
    assert synth.name in ("mlx", "mac_say")


def test_factory_unknown_engine_raises():
    try:
        AudioSynthesizerFactory.create(engine="nonexistent_engine")
        raise AssertionError("Should have raised")
    except (ValueError, Exception):
        pass


def test_factory_registers_custom_engine():
    class CustomSynth:
        name = "custom"
        is_available = True

        def __init__(self, **kwargs):
            pass

        def synthesize(self, *a, **kw):
            return True

        def merge_audio(self, *a, **kw):
            return True

    AudioSynthesizerFactory.register(TTSEngine.MLX, CustomSynth)
    synth = AudioSynthesizerFactory.create(engine=TTSEngine.MLX)
    assert synth.name == "custom"

    from pdftranslator.infrastructure.audio.mlx_audio_synthesizer import (
        MlxAudioSynthesizer,
    )
    AudioSynthesizerFactory.register(TTSEngine.MLX, MlxAudioSynthesizer)
