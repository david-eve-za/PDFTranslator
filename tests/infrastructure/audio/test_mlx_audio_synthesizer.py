"""Tests for MlxAudioSynthesizer."""
from unittest.mock import MagicMock, patch
from pathlib import Path

from pdftranslator.infrastructure.audio.mlx_audio_synthesizer import MlxAudioSynthesizer


def test_mlx_name():
    synth = MlxAudioSynthesizer()
    assert synth.name == "mlx"


def test_mlx_not_available_without_package():
    synth = MlxAudioSynthesizer()
    assert isinstance(synth.is_available, bool)


def test_mlx_synthesize_empty_text():
    synth = MlxAudioSynthesizer()
    result = synth.synthesize("", Path("/tmp/test.m4a"))
    assert result is False


def test_mlx_protocol_compliance():
    from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer

    synth = MlxAudioSynthesizer()
    assert isinstance(synth, AudioSynthesizer)
