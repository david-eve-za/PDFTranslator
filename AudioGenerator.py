import logging
import subprocess
import tempfile
from pathlib import Path

import nltk
from langchain_text_splitters import NLTKTextSplitter
from tqdm import tqdm

# Configure logging for this module
logger = logging.getLogger(__name__)

# Module-level flag and helper function to ensure NLTK 'punkt' is downloaded only once
_NLTK_PUNKT_DOWNLOADED = False


def _ensure_nltk_punkt():
    """
    Ensures that the NLTK 'punkt' tokenizer data is available.
    Downloads it if not found. This function is designed to run once.
    """
    global _NLTK_PUNKT_DOWNLOADED
    if _NLTK_PUNKT_DOWNLOADED:
        return
    try:
        nltk.data.find('tokenizers/punkt')
        logger.debug("NLTK 'punkt' tokenizer found.")
        _NLTK_PUNKT_DOWNLOADED = True
    except (nltk.downloader.DownloadError, LookupError):
        logger.info("NLTK 'punkt' tokenizer not found. Downloading...")
        try:
            nltk.download('punkt', quiet=True)
            logger.info("NLTK 'punkt' tokenizer downloaded successfully.")
            _NLTK_PUNKT_DOWNLOADED = True
        except Exception as e:
            logger.error(f"Failed to download NLTK 'punkt' tokenizer: {e}", exc_info=True)
            # Depending on strictness, you might want to raise an error here
            # or allow the program to continue, potentially failing later.


class AudioGenerator:
    def __init__(self, voice="Paulina", final_output="final_audio.m4a"):
        """
        Initialize the AudioGenerator class.

        Parameters:
        - voice (str): The voice to use for macOS 'say' command.
        - final_output (str or Path): File path for the final merged audio file.
        """
        self.voice = voice
        self.final_output = Path(final_output)  # Store as Path object
        self.output_dir = None  # Will be set to the temporary directory path within process_texts

        _ensure_nltk_punkt()  # Ensure 'punkt' is available

        self.target_text_spliter = NLTKTextSplitter(
            chunk_size=1900,  # Max characters for 'say' command or manageable chunk
            chunk_overlap=0,
            language="spanish"  # NLTKTextSplitter uses this for appropriate sentence tokenization
        )

    def _text_to_audio(self, text_chunk: str, output_audio_file: Path):
        """
        Converts a text chunk to an audio file using macOS's 'say' command.

        Parameters:
        - text_chunk (str): The text to convert.
        - output_audio_file (Path): Path to save the generated audio chunk.
        """
        # Temporary file to pass text to 'say' command, created within the managed temp dir
        # This temp file for text is specific to this call and will be cleaned up with the directory.
        temp_text_file = self.output_dir / f"{output_audio_file.stem}_text.txt"
        try:
            with open(temp_text_file, "w", encoding='utf-8') as f:
                f.write(text_chunk)

            # Using -f to read from file can be more robust for special characters
            subprocess.run(
                ["say", "-v", self.voice, "-o", str(output_audio_file), "-f", str(temp_text_file)],
                check=True,
                capture_output=True, text=True  # Capture output for logging
            )
            logger.info(f"Audio chunk saved: {output_audio_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during text-to-audio conversion for {output_audio_file.name}: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in _text_to_audio for {output_audio_file.name}: {e}", exc_info=True)
            raise
        finally:
            # Clean up the temporary text file immediately if it exists
            if temp_text_file.exists():
                temp_text_file.unlink()

    def _merge_audio_files(self, audio_files: list[Path]):
        """
        Merges multiple .m4a audio files into one using ffmpeg.

        Parameters:
        - audio_files (list[Path]): List of audio file Paths to merge.
        """
        # Create a text file listing all input audio files, within the managed temp dir
        file_list_path = self.output_dir / "ffmpeg_file_list.txt"
        try:
            with open(file_list_path, "w", encoding='utf-8') as f:
                for audio_path in audio_files:
                    # ffmpeg concat demuxer requires relative paths or escaped absolute paths.
                    # Using absolute paths with 'file' directive.
                    f.write(f"file '{audio_path.resolve()}'\n")

            # Ensure final output directory exists
            self.final_output.parent.mkdir(parents=True, exist_ok=True)

            # Use ffmpeg to concatenate the audio files
            # -y: overwrite output files without asking
            # -f concat: use the concat demuxer
            # -safe 0: necessary if using absolute paths in the list file (though relative is often safer)
            # -c:a libfdk_aac: good quality AAC encoder (ensure ffmpeg is compiled with it)
            #   Alternative: -c:a aac (built-in ffmpeg AAC encoder, quality might vary)
            # -b:a 64k: audio bitrate for voice, adjust as needed
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(file_list_path),
                    "-c:a", "aac", "-b:a", "64k",  # Using standard 'aac' for broader compatibility
                    str(self.final_output)
                ],
                check=True,
                capture_output=True, text=True  # Capture output for logging
            )
            logger.info(f"All audio files merged into: {self.final_output}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during audio merging with ffmpeg: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in _merge_audio_files: {e}", exc_info=True)
            raise
        finally:
            # Clean up the temporary file list
            if file_list_path.exists():
                file_list_path.unlink()

    def process_texts(self, text_content: str) -> bool:
        """
        Converts a large text content to individual .m4a audio files for chunks
        and merges them into one final .m4a file.
        Uses a temporary directory for intermediate files, which is cleaned up afterwards.

        Parameters:
        - text_content (str): The entire string content to convert to audio.

        Returns:
        - bool: True if processing was successful, False otherwise.
        """
        if not text_content or not text_content.strip():
            logger.warning("Input text is empty. Skipping audio generation.")
            return False

        if self.final_output.exists():
            logger.info(f"Final output file already exists: {self.final_output}. Skipping.")
            return False  # Or True, depending on desired behavior for existing files

        # Ensure the parent directory for the final output file exists
        try:
            self.final_output.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create parent directory for {self.final_output}: {e}", exc_info=True)
            return False

        chunks = self.target_text_spliter.split_text(text_content)
        if not chunks:
            logger.warning("Text splitting resulted in no chunks. Skipping audio generation.")
            return False

        audio_files_generated = []

        try:
            with tempfile.TemporaryDirectory(prefix="audio_chunks_") as temp_dir_str:
                self.output_dir = Path(temp_dir_str)  # Set self.output_dir for helper methods
                logger.info(f"Using temporary directory for audio chunks: {self.output_dir}")

                for i, chunk_text in tqdm(enumerate(chunks, start=1), total=len(chunks), desc="Generating Audio Chunks",
                                          unit="chunk"):
                    # Normalize common typographic characters that 'say' might misinterpret
                    normalized_chunk = chunk_text \
                        .replace("”", "\"").replace("“", "\"") \
                        .replace("’", "'").replace("‘", "'") \
                        .replace("—", "-").replace("–", "-") \
                        .replace("…", "...") \
                        .replace("<br>", "\n")  # Handle HTML line breaks if any

                    chunk_audio_file = self.output_dir / f"chunk_{i:04d}.m4a"
                    self._text_to_audio(normalized_chunk, chunk_audio_file)
                    audio_files_generated.append(chunk_audio_file)

                if not audio_files_generated:
                    logger.warning("No audio chunks were successfully generated. Cannot merge.")
                    return False  # self.output_dir will be cleaned by 'with' statement

                logger.info(f"Generated {len(audio_files_generated)} audio chunks. Merging...")
                self._merge_audio_files(audio_files_generated)

            # This block executes after the 'with' block has successfully exited (temp dir cleaned)
            logger.info(f"Successfully created final audio: {self.final_output}")
            logger.info(f"Temporary audio processing directory ({self.output_dir}) and its contents have been removed.")
            return True

        except subprocess.CalledProcessError as e:
            # Errors from _text_to_audio or _merge_audio_files if they raise
            # Error message already logged by the helper methods.
            logger.error(f"Audio generation process failed due to a subprocess error.")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during audio processing: {e}", exc_info=True)
            return False
        finally:
            # Ensure self.output_dir is reset if it was set, good practice though
            # TemporaryDirectory handles cleanup of the path it managed.
            self.output_dir = None
