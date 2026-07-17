"""
Audio Generation Activity for Temporal Workflows.

Stage 6: Generate audio from translated text using Rust audio service.

CUPID Principle: Unix Philosophy - Single responsibility: audio generation via external pipeline.
"""

import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from temporalio import activity


@dataclass
class GenerateAudioInput:
    """Input for generate audio activity."""
    job_id: int
    segments: list[dict]
    target_lang: str
    voice: str = "Samantha"
    format: str = "m4a"
    sample_rate: int = 24000
    bitrate: str = "48k"
    normalize: bool = True
    target_loudness: float = -16.0
    engine: str = "macos-say"


@dataclass
class GenerateAudioOutput:
    """Output for generate audio activity."""
    audio_file_path: str | None
    duration_ms: int
    total_chars: int
    errors: list[str]


async def _run_audio_pipeline(
    text: str,
    voice: str,
    format: str,
    sample_rate: int,
    bitrate: str,
    normalize: bool,
    target_loudness: float,
    engine: str,
) -> tuple[bytes, int]:
    """
    Run the pdftranslator-audio binary as a subprocess.

    Returns (audio_bytes, duration_ms)
    """
    # Build command
    cmd = [
        "pdftranslator-audio",
        "--voice", voice,
        "--format", format,
        "--sample-rate", str(sample_rate),
        "--bitrate", bitrate,
        "--normalize" if normalize else "--normalize=false",
        "--target-loudness", str(target_loudness),
        "generate",
    ]

    # Run subprocess with text on stdin
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate(input=text.encode("utf-8"))

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Audio generation failed: {error_msg}")

    # Duration estimation from output size (approximate)
    # For m4a at 48k: ~48000 bits/sec = 6000 bytes/sec
    # For wav at 24000Hz 16-bit mono: 24000 * 2 = 48000 bytes/sec
    if format in ("wav", "aiff"):
        bytes_per_sec = sample_rate * 2  # 16-bit mono
    else:
        bitrate_k = int(bitrate.replace("k", ""))
        bytes_per_sec = bitrate_k * 1000 // 8

    duration_ms = int(len(stdout) / bytes_per_sec * 1000) if bytes_per_sec > 0 else 0

    return stdout, duration_ms


@activity.defn
async def generate_audio_activity(input_data: GenerateAudioInput) -> GenerateAudioOutput:
    """
    Stage 6: Generate audio from translated segments.

    Concatenates all translated segments and synthesizes to audio file
    using the Rust pdftranslator-audio pipeline (EBU R128 normalized).

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: text-to-audio pipeline.
    """
    errors = []

    # Concatenate all translated segments
    translated_texts = []
    total_chars = 0
    for segment in input_data.segments:
        target_text = segment.get("target_text")
        if target_text and target_text.strip():
            translated_texts.append(target_text.strip())
            total_chars += len(target_text)

    if not translated_texts:
        return GenerateAudioOutput(
            audio_file_path=None,
            duration_ms=0,
            total_chars=0,
            errors=["No translated text to synthesize"],
        )

    full_text = " ".join(translated_texts)

    # Create output directory based on job_id
    output_dir = Path(f"/tmp/pdftranslator-audio/job_{input_data.job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_file = output_dir / f"audiobook.{input_data.format}"

    try:
        # Run audio pipeline
        audio_data, duration_ms = await _run_audio_pipeline(
            text=full_text,
            voice=input_data.voice,
            format=input_data.format,
            sample_rate=input_data.sample_rate,
            bitrate=input_data.bitrate,
            normalize=input_data.normalize,
            target_loudness=input_data.target_loudness,
            engine=input_data.engine,
        )

        # Write audio file
        audio_file.write_bytes(audio_data)

        return GenerateAudioOutput(
            audio_file_path=str(audio_file),
            duration_ms=duration_ms,
            total_chars=total_chars,
            errors=errors,
        )

    except Exception as e:
        errors.append(str(e))
        return GenerateAudioOutput(
            audio_file_path=None,
            duration_ms=0,
            total_chars=total_chars,
            errors=errors,
        )


# Wrapper to match the naming convention expected by workflow imports
async def generate_audio_activity_wrapper(input_data: GenerateAudioInput) -> GenerateAudioOutput:
    """Wrapper for generate_audio_activity to match import pattern."""
    return await generate_audio_activity(input_data)