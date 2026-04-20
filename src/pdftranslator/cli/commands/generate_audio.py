"""Generate audio from translated chapters/volumes."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from pdftranslator.cli.app import console
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.tools.AudioGenerator import AudioGenerator

logger = logging.getLogger(__name__)


def generate_audio(
    chapter_id: Optional[int] = typer.Option(
        None, "--chapter-id", "-c", help="Chapter ID to generate audio for"
    ),
    volume_id: Optional[int] = typer.Option(
        None, "--volume-id", "-v", help="Volume ID to generate audio for all chapters"
    ),
    voice: Optional[str] = typer.Option(
        None, "--voice", help="TTS voice (default: from config)"
    ),
) -> None:
    """
    Generate audio from translated text in database.

    Examples:
        python PDFAgent.py generate-audio --chapter-id 123
        python PDFAgent.py generate-audio --volume-id 5
        python PDFAgent.py generate-audio --volume-id 5 --voice "Paulina"
    """
    if chapter_id is not None and volume_id is not None:
        console.print(
            "[red]Error: Specify only one of --chapter-id or --volume-id[/red]"
        )
        raise typer.Exit(1)

    if chapter_id is None and volume_id is None:
        console.print("[red]Error: Must specify --chapter-id or --volume-id[/red]")
        raise typer.Exit(1)

    settings = Settings.get()
    selected_voice = voice or settings.processing.voice

    if chapter_id is not None:
        _generate_chapter_audio(chapter_id, selected_voice)
    else:
        _generate_volume_audio(volume_id, selected_voice)


def _generate_chapter_audio(chapter_id: int, voice: str) -> None:
    """Generate audio for a single chapter."""
    pool = DatabasePool.get_instance()
    chapter_repo = ChapterRepository(pool)
    volume_repo = VolumeRepository(pool)
    work_repo = BookRepository(pool)

    chapter = chapter_repo.get_by_id(chapter_id)
    if chapter is None:
        console.print(f"[red]Error: Chapter with ID {chapter_id} not found[/red]")
        raise typer.Exit(1)

    if not chapter.translated_text or not chapter.translated_text.strip():
        console.print(f"[red]Error: Chapter {chapter_id} has no translated text[/red]")
        raise typer.Exit(1)

    volume = volume_repo.get_by_id(chapter.volume_id)
    if volume is None:
        console.print(f"[red]Error: Volume with ID {chapter.volume_id} not found[/red]")
        raise typer.Exit(1)

    work = work_repo.get_by_id(volume.work_id)
    if work is None:
        console.print(f"[red]Error: Work with ID {volume.work_id} not found[/red]")
        raise typer.Exit(1)

    settings = Settings.get()
    work_title = work.title.replace(" ", "_")
    output_dir = (
        settings.paths.audiobooks_dir / work_title / f"Vol{volume.volume_number}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = (
        output_dir
        / f"{work_title}_Vol{volume.volume_number}_Ch{chapter.chapter_number:03d}.m4a"
    )

    if output_filename.exists():
        console.print(f"[yellow]Audio file already exists: {output_filename}[/yellow]")
        console.print("[yellow]Skipping.[/yellow]")
        return

    console.print(
        f"[cyan]Generating audio for Chapter {chapter.chapter_number}...[/cyan]"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating audio...", total=None)

        audio_generator = AudioGenerator(progress=progress)
        success = audio_generator.process_texts(
            text_content=chapter.translated_text,
            output_filename=output_filename,
        )

        if success:
            progress.update(
                task, description=f"[green]✓ Audio saved: {output_filename}[/green]"
            )
        else:
            progress.update(task, description=f"[red]✗ Failed to generate audio[/red]")
            raise typer.Exit(1)


def _generate_volume_audio(volume_id: int, voice: str) -> None:
    """Generate audio for all chapters in a volume."""
    pool = DatabasePool.get_instance()
    chapter_repo = ChapterRepository(pool)
    volume_repo = VolumeRepository(pool)
    work_repo = BookRepository(pool)

    volume = volume_repo.get_by_id(volume_id)
    if volume is None:
        console.print(f"[red]Error: Volume with ID {volume_id} not found[/red]")
        raise typer.Exit(1)

    work = work_repo.get_by_id(volume.work_id)
    if work is None:
        console.print(f"[red]Error: Work with ID {volume.work_id} not found[/red]")
        raise typer.Exit(1)

    chapters = chapter_repo.get_by_volume(volume_id)
    if not chapters:
        console.print(f"[yellow]No chapters found in volume {volume_id}[/yellow]")
        return

    console.print(f"[cyan]Generating audio for {len(chapters)} chapters...[/cyan]")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for chapter in chapters:
        if not chapter.translated_text or not chapter.translated_text.strip():
            console.print(
                f"[yellow]Skipping Chapter {chapter.chapter_number}: no translated text[/yellow]"
            )
            skip_count += 1
            continue

        settings = Settings.get()
        work_title = work.title.replace(" ", "_")
        output_dir = (
            settings.paths.audiobooks_dir / work_title / f"Vol{volume.volume_number}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filename = (
            output_dir
            / f"{work_title}_Vol{volume.volume_number}_Ch{chapter.chapter_number:03d}.m4a"
        )

        if output_filename.exists():
            console.print(
                f"[dim]Skipping Chapter {chapter.chapter_number}: file exists[/dim]"
            )
            skip_count += 1
            continue

        try:
            audio_generator = AudioGenerator()
            success = audio_generator.process_texts(
                text_content=chapter.translated_text,
                output_filename=output_filename,
            )

            if success:
                console.print(
                    f"[green]✓ Chapter {chapter.chapter_number}: {output_filename.name}[/green]"
                )
                success_count += 1
            else:
                console.print(
                    f"[red]✗ Chapter {chapter.chapter_number}: generation failed[/red]"
                )
                fail_count += 1
        except Exception as e:
            logger.error(f"Error generating audio for chapter {chapter.id}: {e}")
            console.print(f"[red]✗ Chapter {chapter.chapter_number}: {e}[/red]")
            fail_count += 1

    console.print()
    console.print(
        f"[cyan]Summary: {success_count} succeeded, {skip_count} skipped, {fail_count} failed[/cyan]"
    )

    if fail_count > 0:
        raise typer.Exit(1)
