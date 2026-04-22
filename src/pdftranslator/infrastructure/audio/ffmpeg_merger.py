"""FFmpeg-based audio merging utility.

Extracted from AudioGenerator._merge_audio_files for SRP-7 compliance.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def merge_audio_files(audio_files: list[Path], output_path: Path) -> bool:
    """Merge multiple audio files into one using ffmpeg.

    Args:
        audio_files: List of audio file paths to merge.
        output_path: Path for the merged output file.

    Returns:
        True on success, False on failure.
    """
    if not audio_files:
        return False

    with tempfile.TemporaryDirectory(prefix="ffmpeg_merge_") as temp_dir:
        file_list_path = Path(temp_dir) / "ffmpeg_file_list.txt"
        try:
            with open(file_list_path, "w", encoding="utf-8") as f:
                for audio_path in audio_files:
                    f.write(f"file '{audio_path.resolve()}'\n")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(file_list_path),
                    "-filter_complex",
                    "[0:a]loudnorm=I=-16:LRA=11:TP=-1.5,compand=attacks=0.02:decays=0.1:points=-80/-80|-30/-10|-20/-8|0/0,highpass=f=80,lowpass=f=12000,aresample=24000,pan=stereo|c0=c0|c1=c0[a]",
                    "-map", "[a]",
                    "-ac", "1",
                    "-c:a", "libfdk_aac",
                    "-b:a", "48k",
                    "-ar", "24000",
                    "-profile:a", "aac_he",
                    "-vn",
                    "-compression_level", "12",
                    "-cutoff", "12000",
                    "-movflags", "+faststart",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"All audio files merged into: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during audio merging with ffmpeg: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in merge_audio_files: {e}", exc_info=True)
            return False
