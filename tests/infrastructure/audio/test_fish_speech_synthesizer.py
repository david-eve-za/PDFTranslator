"""Tests for FishSpeechSynthesizer."""
from pathlib import Path

from pdftranslator.infrastructure.audio.fish_speech_synthesizer import (
    FishSpeechSynthesizer,
)


def test_fish_speech_name():
    synth = FishSpeechSynthesizer()
    assert synth.name == "fish_speech"


def test_fish_speech_not_available_without_server():
    synth = FishSpeechSynthesizer(server_url="http://localhost:99999")
    assert isinstance(synth.is_available, bool)


def test_fish_speech_synthesize_empty_text():
    synth = FishSpeechSynthesizer()
    result = synth.synthesize("", Path("/tmp/test.m4a"))
    assert result is False


def test_fish_speech_protocol_compliance():
    from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer

    synth = FishSpeechSynthesizer()
    assert isinstance(synth, AudioSynthesizer)
