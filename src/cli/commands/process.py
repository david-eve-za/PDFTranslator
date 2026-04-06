import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple

import typer
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from src.cli.app import (
    app,
    console,
    setup_logging,
    print_summary_table,
    validate_output_format,
    LOG_FILE_NAME,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_FILE_TYPE_TO_PROCESS,
)
from src.core.config.settings import Settings
from src.tools.VideoGenerator import VideoGenerator
from src.tools.AudioGenerator import AudioGenerator
from src.tools.FileFinder import FileFinder, IsFileFilter, ExcludeTranslatedFilter
from src.tools.TextExtractor import TextExtractor
from src.tools.Translator import Translator


def translate_text(translator: Translator, text: str, file_path: Path) -> Optional[str]:
    config = GlobalConfig()
    logging.info(f" - Translating text for: {os.path.basename(file_path)}")
    translated_text = translator.translate_text(
        text, config.source_lang, config.target_lang
    )
    if not translated_text or not translated_text.strip():
        logging.warning(
            f" - Translation failed or resulted in empty text for {os.path.basename(file_path)}. Skipping file."
        )
        return None
    logging.info(
        f" - Text translated and cleaned (length: {len(translated_text)} characters)"
    )
    return translated_text


def generate_audio(
    audio_generator: AudioGenerator, text: str, output_filename: Path, file_path: Path
) -> bool:
    logging.info(f" - Generating audio for: {os.path.basename(file_path)}")
    try:
        success = audio_generator.process_texts(
            text_content=text.replace("<!-- image -->", "").strip(),
            output_filename=output_filename,
        )
    except Exception as e:
        logging.error(
            f" - Error during audio generation for {os.path.basename(file_path)}: {e}"
        )
        return False
    return success


def generate_video(
    video_generator: VideoGenerator,
    images_list: List[Path],
    audio_path: Path,
    file_path: Path,
) -> bool:
    config = GlobalConfig()
    if not images_list:
        logging.info(" - No images found, skipping video generation.")
        return True

    logging.info(f" - Found {len(images_list)} images. Attempting to generate video.")
    output_video_path = audio_path.with_suffix(".mp4")
    try:
        video_generator.create_video_from_images_and_audio(
            image_paths=images_list,
            audio_path=audio_path,
            output_video_path=output_video_path,
            fps=1,
        )
        logging.info(f" - Video created successfully at: {output_video_path}")
        return True
    except Exception as e:
        logging.error(
            f" - Error during video generation for {os.path.basename(file_path)}: {e}"
        )
        return False


def prepare_output_paths(file_path: Path) -> Optional[Tuple[Path, Path]]:
    config = GlobalConfig()
    try:
        file_parent_dir = file_path.parent.resolve()
        dynamic_output_dir = file_parent_dir / DEFAULT_OUTPUT_SUBDIR
        dynamic_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f" - Output directory: {dynamic_output_dir}")
    except OSError as e:
        logging.error(
            f" - Error creating output directory for {os.path.basename(file_path)}: {e}"
        )
        return None

    base_name = file_path.stem
    output_audio_filename = (
        dynamic_output_dir / f"{base_name}_{config.target_lang}.{config.output_format}"
    )
    return dynamic_output_dir, output_audio_filename


def process_single_file(file_path: Path, services: Tuple) -> bool:
    config = GlobalConfig()
    translation_agent, audio_generator, video_generator = services

    logging.info(f"\n--- Processing file: {os.path.basename(file_path)} ---")

    output_paths = prepare_output_paths(file_path)
    if not output_paths:
        return False
    _, output_audio_filename = output_paths

    if output_audio_filename.exists():
        logging.info(
            f" - Audio file already exists: {output_audio_filename}. Skipping."
        )
        return True

    text_extractor = TextExtractor()
    original_text = text_extractor.extract_text(file_path=file_path)

    if not original_text or not original_text.strip():
        logging.warning(
            f" - Could not extract text or text is empty for {os.path.basename(file_path)}. Skipping file."
        )
        return False
    logging.info(
        f" - Original text extracted (length: {len(original_text)} characters)"
    )

    temp_text_filename = f"{file_path.stem}_review.txt"
    temp_text_file_path = Path("reviewer") / temp_text_filename
    temp_text_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(temp_text_file_path, "w", encoding="utf-8") as f:
            f.write(original_text)

        logging.info(
            f"\n--- Texto extraído guardado para validación en: {temp_text_file_path} ---"
        )
        logging.info(
            "Por favor, revise el archivo y pulse Enter para continuar o Ctrl+C para cancelar."
        )
        input()

        with open(temp_text_file_path, "r", encoding="utf-8") as f:
            original_text = f.read()

    except Exception as e:
        logging.error(f"Error durante la validación del usuario: {e}")
        return False
    finally:
        if temp_text_file_path.exists():
            temp_text_file_path.unlink()
            logging.info(f"Archivo temporal eliminado: {temp_text_file_path}")

    translated_text = translate_text(translation_agent, original_text, file_path)
    if translated_text is None:
        return False

    audio_success = generate_audio(
        audio_generator, translated_text, output_audio_filename, file_path
    )
    if not audio_success:
        logging.error(
            f"--- Processing failed (audio) for: {os.path.basename(file_path)} ---"
        )
        return False

    if config.gen_video:
        video_success = generate_video(
            video_generator, [], output_audio_filename, file_path
        )
        if not video_success:
            logging.error(
                f"--- Processing failed (video) for: {os.path.basename(file_path)} ---"
            )
            return False

    logging.info(f"--- Processing completed for: {os.path.basename(file_path)} ---")
    return True


def initialize_services() -> Optional[Tuple]:
    try:
        translation_agent = Translator()
        audio_generator = AudioGenerator()
        video_generator = VideoGenerator()
        return (
            translation_agent,
            audio_generator,
            video_generator,
        )
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        return None


def process_files_with_progress(services: Tuple) -> Tuple[int, int]:
    config = GlobalConfig()
    file_finder = FileFinder(config.input_path)

    files_to_process: List[Path] = file_finder.get_files(
        file_type=DEFAULT_FILE_TYPE_TO_PROCESS,
        filters=[IsFileFilter(), ExcludeTranslatedFilter()],
    )

    if not files_to_process:
        console.print(
            f"[yellow]No .{DEFAULT_FILE_TYPE_TO_PROCESS} files found in '{config.input_path}'[/yellow]"
        )
        return 0, 0

    console.print(f"[green]Found {len(files_to_process)} files to process[/green]")

    successful_file_count = 0
    failed_file_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Processing files...", total=len(files_to_process)
        )

        for file_path in files_to_process:
            progress.update(task, description=f"[cyan]Processing: {file_path.name}")
            success = process_single_file(file_path, services)
            if success:
                successful_file_count += 1
            else:
                failed_file_count += 1
            progress.advance(task)

    return successful_file_count, failed_file_count


@app.command()
def process(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        help="Path to the directory or file to process",
    ),
    source_lang: str = typer.Option(
        "en-US", "--source-lang", "-sl", help="Source language"
    ),
    target_lang: str = typer.Option(
        "es-MX", "--target-lang", "-tl", help="Target language"
    ),
    output_format: str = typer.Option(
        "m4a",
        "--format",
        "-f",
        help="Final audio file format (m4a, mp3, aiff, wav)",
        callback=validate_output_format,
    ),
    voice: str = typer.Option(
        "Paulina", "--voice", help="macOS 'say' voice for the target language"
    ),
    gen_video: bool = typer.Option(False, "--gen-video", help="Generate a video"),
    agent: str = typer.Option(
        "nvidia",
        "--agent",
        "-a",
        help="The agent for translation (nvidia, gemini, ollama)",
    ),
):
    """
    Orchestrates the process of finding files, extracting text,
    translating, and generating audiobooks.
    """
    setup_logging()
    config = GlobalConfig()

    config.update_from_dict(
        {
            "input_path": str(input_path),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "output_format": output_format,
            "voice": voice,
            "gen_video": gen_video,
            "agent": agent,
        }
    )

    console.print(
        Panel.fit(
            f"[bold blue]PDFAgent[/bold blue] - Audiobook Generator",
            subtitle=f"Processing: {input_path.name}",
        )
    )

    services = initialize_services()
    if not services:
        console.print("[red]Error initializing services[/red]")
        raise typer.Exit(1)

    successful_file_count = 0
    failed_file_count = 0

    if input_path.is_file():
        console.print(f"[cyan]Processing single file:[/cyan] {input_path.name}")
        if process_single_file(input_path, services):
            successful_file_count = 1
        else:
            failed_file_count = 1
    elif input_path.is_dir():
        console.print(f"[cyan]Processing directory:[/cyan] {input_path}")
        successful_file_count, failed_file_count = process_files_with_progress(services)
    else:
        console.print(f"[red]Invalid path: {input_path}[/red]")
        raise typer.Exit(1)

    print_summary_table(successful_file_count, failed_file_count)
