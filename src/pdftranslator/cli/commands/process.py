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

from pdftranslator.cli.app import (
    app,
    console,
    setup_logging,
    print_summary_table,
    validate_output_format,
    LOG_FILE_NAME,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_FILE_TYPE_TO_PROCESS,
)
from pdftranslator.core.config.settings import Settings
from pdftranslator.infrastructure.llm.base import BCP47Language
from pdftranslator.infrastructure.llm.factory import LLMFactory
from pdftranslator.application.services.translation_service import TranslationService
from pdftranslator.tools.FileFinder import FileFinder, IsFileFilter, ExcludeTranslatedFilter
from pdftranslator.infrastructure.document.docling_document_parser import DoclingDocumentParser
from pdftranslator.infrastructure.audio.audio_synthesizer_factory import AudioSynthesizerFactory
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer


def translate_text(
    translator: TranslationService,
    text: str,
    file_path: Path,
    source_lang: str,
    target_lang: str,
) -> Optional[str]:
    logging.info(f" - Translating text for: {os.path.basename(file_path)}")
    language = _get_language_for_split(source_lang)
    result = translator.translate(text, source_lang, target_lang, language=language)
    translated_text = result.text
    if not translated_text or not translated_text.strip():
        logging.warning(
            f" - Translation failed or resulted in empty text for {os.path.basename(file_path)}. Skipping file."
        )
        return None
    logging.info(
        f" - Text translated and cleaned (length: {len(translated_text)} characters)"
    )
    return translated_text


def _get_language_for_split(source_lang: str) -> BCP47Language:
    lang_map = {
        "en": BCP47Language.ENGLISH,
        "es": BCP47Language.SPANISH,
        "zh": BCP47Language.CHINESE,
        "ja": BCP47Language.JAPANESE,
        "ko": BCP47Language.KOREAN,
        "fr": BCP47Language.FRENCH,
        "de": BCP47Language.GERMAN,
        "it": BCP47Language.ITALIAN,
        "pt": BCP47Language.PORTUGUESE,
        "ru": BCP47Language.RUSSIAN,
        "ar": BCP47Language.ARABIC,
        "hi": BCP47Language.HINDI,
    }
    return lang_map.get(source_lang.lower(), BCP47Language.ENGLISH)


def generate_audio(
    synthesizer: AudioSynthesizer, text: str, output_filename: Path, file_path: Path
) -> bool:
    logging.info(f" - Generating audio for: {os.path.basename(file_path)}")
    try:
        success = synthesizer.synthesize(
            text=text.replace("<!-- image -->", "").strip(),
            output_path=output_filename,
        )
    except Exception as e:
        logging.error(
            f" - Error during audio generation for {os.path.basename(file_path)}: {e}"
        )
        return False
    return success


def prepare_output_paths(
    file_path: Path, target_lang: str, output_format: str
) -> Optional[Tuple[Path, Path]]:
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
        dynamic_output_dir / f"{base_name}_{target_lang}.{output_format}"
    )
    return dynamic_output_dir, output_audio_filename


def process_single_file(
    file_path: Path,
    translator: TranslationService,
    synthesizer: AudioSynthesizer,
    source_lang: str,
    target_lang: str,
    output_format: str,
) -> bool:
    logging.info(f"\n--- Processing file: {os.path.basename(file_path)} ---")

    output_paths = prepare_output_paths(file_path, target_lang, output_format)
    if not output_paths:
        return False
    _, output_audio_filename = output_paths

    if output_audio_filename.exists():
        logging.info(
            f" - Audio file already exists: {output_audio_filename}. Skipping."
        )
        return True

    text_extractor = DoclingDocumentParser()
    original_text = text_extractor.parse(file_path=str(file_path))

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

    translated_text = translate_text(
        translator, original_text, file_path, source_lang, target_lang
    )
    if translated_text is None:
        return False

    audio_success = generate_audio(
        synthesizer, translated_text, output_audio_filename, file_path
    )
    if not audio_success:
        logging.error(
            f"--- Processing failed (audio) for: {os.path.basename(file_path)} ---"
        )
        return False

    logging.info(f"--- Processing completed for: {os.path.basename(file_path)} ---")
    return True


def initialize_services() -> Optional[Tuple]:
    try:
        llm_client = LLMFactory.create()
        translation_agent = TranslationService(llm_client)
        synthesizer = AudioSynthesizerFactory.create()
        return (
            translation_agent,
            synthesizer,
        )
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        return None


def process_files_with_progress(
    translator: TranslationService,
    synthesizer: AudioSynthesizer,
    input_path: Path,
    source_lang: str,
    target_lang: str,
    output_format: str,
) -> Tuple[int, int]:
    file_finder = FileFinder(input_path)

    files_to_process: List[Path] = file_finder.get_files(
        file_type=DEFAULT_FILE_TYPE_TO_PROCESS,
        filters=[IsFileFilter(), ExcludeTranslatedFilter()],
    )

    if not files_to_process:
        console.print(
            f"[yellow]No .{DEFAULT_FILE_TYPE_TO_PROCESS} files found in '{input_path}'[/yellow]"
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
        success = process_single_file(
            file_path, translator, synthesizer, source_lang,
            target_lang, output_format,
        )
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
        "--format", "-f",
        help="Final audio file format (m4a, mp3, aiff, wav)",
        callback=validate_output_format,
    ),
    voice: str = typer.Option(
        "Paulina", "--voice", help="TTS voice for the target language"
    ),
    agent: str = typer.Option(
        "nvidia", "--agent", "-a", help="The agent for translation (nvidia, gemini, ollama)"
    ),
):
    setup_logging()

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

    translator, synthesizer = services

    successful_file_count = 0
    failed_file_count = 0

    source_lang_code = source_lang.split("-")[0]
    target_lang_code = target_lang.split("-")[0]

    if input_path.is_file():
        console.print(f"[cyan]Processing single file:[/cyan] {input_path.name}")
        if process_single_file(
            input_path, translator, synthesizer,
            source_lang_code, target_lang_code, output_format,
        ):
            successful_file_count = 1
        else:
            failed_file_count = 1
    elif input_path.is_dir():
        console.print(f"[cyan]Processing directory:[/cyan] {input_path}")
        successful_file_count, failed_file_count = process_files_with_progress(
            translator, synthesizer,
            input_path, source_lang_code, target_lang_code, output_format,
        )
    else:
        console.print(f"[red]Invalid path: {input_path}[/red]")
        raise typer.Exit(1)

    print_summary_table(successful_file_count, failed_file_count)
