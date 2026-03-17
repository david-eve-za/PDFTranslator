import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Tuple
import tempfile

from GlobalConfig import GlobalConfig
from tools.VideoGenerator import VideoGenerator
from tools.AudioGenerator import AudioGenerator
from tools.FileFinder import FilesFinder, IsFileFilter, ExcludeTranslatedFilter
from tools.TextExtractor import TextExtractorAgent
from tools.Translator import TranslatorAgent

import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")

# --- Constants ---
LOG_FILE_NAME = "PDFAgent.log"
DEFAULT_OUTPUT_SUBDIR = "audiobooks"
DEFAULT_FILE_TYPE_TO_PROCESS = "pdf"
CONFIG_FILE_NAME = "config.json"


# --- Logging Setup ---
def setup_logging():
    """Configures logging to stream to stdout and a log file."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(LOG_FILE_NAME)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def translate_text(translator: TranslatorAgent, text: str, file_path: Path) -> Optional[str]:
    """
    Translates the given text.
    """
    config = GlobalConfig()
    logging.info(f"  - Translating text for: {os.path.basename(file_path)}")
    translated_text = translator.translate_text(text, config.source_lang, config.target_lang)
    if not translated_text or not translated_text.strip():
        logging.warning(
            f"  - Translation failed or resulted in empty text for {os.path.basename(file_path)}. Skipping file.")
        return None
    logging.info(f"  - Text translated and cleaned (length: {len(translated_text)} characters)")
    return translated_text


def generate_audio(audio_generator: AudioGenerator, text: str, output_filename: Path, file_path: Path) -> bool:
    """
    Generates audio from the given text.
    """
    logging.info(f"  - Generating audio for: {os.path.basename(file_path)}")
    try:
        success = audio_generator.process_texts(text_content=text.replace("<!-- image -->", "").strip(),
                                                output_filename=output_filename)
    except Exception as e:
        logging.error(f"  - Error during audio generation for {os.path.basename(file_path)}: {e}")
        return False
    return success


def generate_video(video_generator: VideoGenerator, images_list: List[Path], audio_path: Path,
                   file_path: Path) -> bool:
    """
    Generates a video from images and an audio file.
    """
    config = GlobalConfig()
    if not images_list:
        logging.info("  - No images found, skipping video generation.")
        return True

    logging.info(f"  - Found {len(images_list)} images. Attempting to generate video.")
    output_video_path = audio_path.with_suffix(".mp4")
    try:
        video_generator.create_video_from_images_and_audio(
            image_paths=images_list,
            audio_path=audio_path,
            output_video_path=output_video_path,
            fps=1
        )
        logging.info(f"  - Video created successfully at: {output_video_path}")
        return True
    except Exception as e:
        logging.error(f"  - Error during video generation for {os.path.basename(file_path)}: {e}")
        return False


def prepare_output_paths(file_path: Path) -> Optional[Tuple[Path, Path]]:
    """
    Prepares the output directory and filenames.
    """
    config = GlobalConfig()
    try:
        file_parent_dir = file_path.parent.resolve()
        dynamic_output_dir = file_parent_dir / DEFAULT_OUTPUT_SUBDIR
        dynamic_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"  - Output directory: {dynamic_output_dir}")
    except OSError as e:
        logging.error(f"  - Error creating output directory for {os.path.basename(file_path)}: {e}")
        return None

    base_name = file_path.stem
    output_audio_filename = dynamic_output_dir / f"{base_name}_{config.target_lang}.{config.output_format}"
    return dynamic_output_dir, output_audio_filename


def process_single_file(file_path: Path, services: Tuple) -> bool:
    """
    Processes a single file: extracts text, translates, generates audio, and optionally a video.
    """
    config = GlobalConfig()
    translation_agent, audio_generator, video_generator = services

    logging.info(f"\n--- Processing file: {os.path.basename(file_path)} ---")

    output_paths = prepare_output_paths(file_path)
    if not output_paths:
        return False
    _, output_audio_filename = output_paths

    if output_audio_filename.exists():
        logging.info(f"  - Audio file already exists: {output_audio_filename}. Skipping.")
        return True

    text_extractor = TextExtractorAgent()
    original_text, images_list = text_extractor.extract_text(file_path=file_path)

    if not original_text or not original_text.strip():
        logging.warning(
            f"  - Could not extract text or text is empty for {os.path.basename(file_path)}. Skipping file.")
        return False
    logging.info(f"  - Original text extracted (length: {len(original_text)} characters)")

    # --- User Validation Step ---
    temp_text_filename = f"{file_path.stem}_review.txt"
    temp_text_file_path = Path("reviewer") / temp_text_filename
    temp_text_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure temp dir exists

    try:
        with open(temp_text_file_path, "w", encoding="utf-8") as f:
            f.write(original_text)

        logging.info(f"\n--- Texto extraído guardado para validación en: {temp_text_file_path} ---")
        logging.info("Por favor, revise el archivo y pulse Enter para continuar o Ctrl+C para cancelar.")
        input() # Wait for user to press Enter

        with open(temp_text_file_path, "r", encoding="utf-8") as f:
            original_text = f.read()

    except Exception as e:
        logging.error(f"Error durante la validación del usuario: {e}")
        return False
    finally:
        if temp_text_file_path.exists():
            temp_text_file_path.unlink()
            logging.info(f"Archivo temporal eliminado: {temp_text_file_path}")
    # --- End User Validation Step ---


    translated_text = translate_text(translation_agent, original_text, file_path)
    if translated_text is None:
        return False

    audio_success = generate_audio(audio_generator, translated_text, output_audio_filename, file_path)
    if not audio_success:
        logging.error(f"--- Processing failed (audio) for: {os.path.basename(file_path)} ---")
        return False

    if config.gen_video:
        video_success = generate_video(video_generator, images_list, output_audio_filename, file_path)
        if not video_success:
            logging.error(f"--- Processing failed (video) for: {os.path.basename(file_path)} ---")
            return False

    logging.info(f"--- Processing completed for: {os.path.basename(file_path)} ---")
    return True


def initialize_services() -> Optional[Tuple]:
    """
    Initializes and returns all the necessary service objects.
    """
    try:
        # config = GlobalConfig() # Get the global config
        # if Path(config.input_path).is_dir():
        #     file_finder = FilesFinder(config.input_path) # FilesFinder needs input_path to initialize
        translation_agent = TranslatorAgent()
        audio_generator = AudioGenerator()
        video_generator = VideoGenerator()
        return translation_agent, audio_generator, video_generator # FilesFinder is not passed, it's used directly in process_files
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        return None


def process_files(services: Tuple) -> Tuple[int, int]:
    """
    Finds and processes all the files.
    """
    config = GlobalConfig()
    file_finder = FilesFinder(config.input_path) # Re-initialize FileFinder here for consistency

    files_to_process: List[Path] = file_finder.get_files(
        file_type=DEFAULT_FILE_TYPE_TO_PROCESS,
        filters=[IsFileFilter(), ExcludeTranslatedFilter()]
    )

    if not files_to_process:
        logging.info(f"No .{DEFAULT_FILE_TYPE_TO_PROCESS} files found in '{config.input_path}'.")
        return 0, 0

    logging.info(f"Found {len(files_to_process)} .{DEFAULT_FILE_TYPE_TO_PROCESS} file(s) to process.")

    successful_file_count = 0
    failed_file_count = 0

    for file_path in files_to_process:
        success = process_single_file(file_path, services)
        if success:
            successful_file_count += 1
        else:
            failed_file_count += 1

    return successful_file_count, failed_file_count


def main():
    """
    Orchestrates the process of finding files, extracting text,
    translating, and generating audiobooks.
    """
    setup_logging()
    config = GlobalConfig()

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Audiobook Generator from PDF/EPUB with AI Translation")
    parser.add_argument("input_path", type=str, nargs='?', default=None,
                        help="Path to the directory or file to process. Overrides config file.")
    parser.add_argument("-sl", "--source_lang", help="Source language.")
    parser.add_argument("-tl", "--target_lang", help="Target language.")
    parser.add_argument("--output_format", choices=['m4a', 'mp3', 'aiff', 'wav'], help="Final audio file format.")
    parser.add_argument("--voice", help="macOS 'say' voice for the target language.")
    parser.add_argument("--gen_video", action="store_true", help="Generate a video.")
    parser.add_argument("--agent", choices=['gemini', 'ollama'], help="The agent for translation.")
    args = parser.parse_args()

    # --- Configuration Loading ---
    try:
        config.load(CONFIG_FILE_NAME)
        logging.info(f"Loaded configuration from {CONFIG_FILE_NAME}")
    except FileNotFoundError:
        logging.info(f"{CONFIG_FILE_NAME} not found. Using default settings and command-line arguments.")
    except ValueError as e:
        logging.error(f"Error loading {CONFIG_FILE_NAME}: {e}. Please check the file format.")
        return

    # Override with command-line arguments
    config.update_from_args(args)

    if not config.input_path:
        logging.error("Input path is not specified in config.json or as a command-line argument. Exiting.")
        parser.print_help()
        return

    # --- Save final config ---
    config.save(CONFIG_FILE_NAME)
    logging.info(f"Final configuration saved to {CONFIG_FILE_NAME}")

    input_path = Path(config.input_path)

    if not input_path.exists():
        logging.error(f"The input path does not exist: {input_path}")
        return

    services = initialize_services()
    if not services:
        return

    successful_file_count = 0
    failed_file_count = 0

    if input_path.is_file():
        logging.info(f"Processing a single file: {input_path.name}")
        if process_single_file(input_path, services):
            successful_file_count = 1
        else:
            failed_file_count = 1
    elif input_path.is_dir():
        logging.info(f"Processing a directory: {input_path}")
        successful_file_count, failed_file_count = process_files(services)
    else:
        logging.error(f"The input path is not a valid file or directory: {input_path}")
        return

    logging.info("\n--- Process Summary ---")
    logging.info("Processing finished.")
    logging.info(f"Successfully processed/skipped files: {successful_file_count}")
    logging.info(f"Failed files: {failed_file_count}")
    logging.info(f"Log files are located in: {LOG_FILE_NAME}")


if __name__ == "__main__":

    main()
