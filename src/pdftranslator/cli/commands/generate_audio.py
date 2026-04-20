"""Generate audio from translated chapters/volumes."""

import logging
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pdftranslator.cli.app import app, console, setup_logging
from pdftranslator.core.config.settings import Settings
from pdftranslator.core.models.work import Work, Volume, Chapter
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.tools.AudioGenerator import AudioGenerator

logger = logging.getLogger(__name__)

SCOPE_ALL_BOOK = "all_book"
SCOPE_ALL_VOLUME = "all_volume"
SCOPE_SINGLE_CHAPTER = "single_chapter"


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    """Sort key for chapters: Prologue, numbered chapters, Epilogue."""
    if chapter.chapter_number is None:
        title_lower = (chapter.title or "").lower()
        if "prologue" in title_lower:
            return (0, 0)
        elif "epilogue" in title_lower:
            return (2, 0)
        else:
            return (1, 0)
    else:
        return (1, chapter.chapter_number)


def _format_chapter_display(chapter: Chapter) -> str:
    """Format a chapter for display."""
    if chapter.chapter_number is None:
        return f"{chapter.title or 'Unknown'}"
    else:
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"


def _select_work_interactive(work_repo: BookRepository) -> Optional[Work]:
    """Interactive selection of a work from the database."""
    works = work_repo.find_all()
    if not works:
        console.print("[yellow]No works found in database.[/yellow]")
        return None

    work_choices = [questionary.Choice(title=w.title, value=w) for w in works]

    selected_work: Optional[Work] = questionary.select(
        "Select a work:",
        choices=work_choices,
    ).ask()

    return selected_work


def _display_work_structure(
    work: Work, volume_repo: VolumeRepository, chapter_repo: ChapterRepository
) -> dict:
    """Display the structure of a work with audio status."""
    if work.id is None:
        return {"volumes": 0, "chapters": 0, "generated": 0, "pending": 0}

    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return {"volumes": 0, "chapters": 0, "generated": 0, "pending": 0}

    settings = Settings.get()
    work_title = work.title.replace(" ", "_")

    total_chapters = 0
    total_generated = 0
    total_pending = 0

    console.print(f"\n[bold]📚 {work.title}[/bold]\n")

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        chapters = chapter_repo.get_by_volume(volume.id) if volume.id else []

        generated = 0
        pending = 0
        for ch in chapters:
            if ch.translated_text:
                output_path = (
                    settings.paths.audiobooks_dir
                    / work_title
                    / f"Vol{volume.volume_number}"
                    / f"{work_title}_Vol{volume.volume_number}_Ch{ch.chapter_number:03d}.m4a"
                )
                if output_path.exists():
                    generated += 1
                else:
                    pending += 1

        total_chapters += len(chapters)
        total_generated += generated
        total_pending += pending

        vol_title = f" - {volume.title}" if volume.title else ""
        status = ""
        if generated == len(chapters) and len(chapters) > 0:
            status = "[green] ✓ all audio generated[/green]"
        elif generated > 0:
            status = f"[yellow] ({generated}/{len(chapters)} generated)[/yellow]"
        elif len(chapters) > 0:
            status = "[dim] (no audio)[/dim]"

        console.print(
            f"  [cyan]Volume {volume.volume_number}{vol_title}[/cyan]{status}"
        )

        for ch in sorted(chapters, key=_get_chapter_sort_key)[:5]:
            ch_display = _format_chapter_display(ch)
            output_path = (
                settings.paths.audiobooks_dir
                / work_title
                / f"Vol{volume.volume_number}"
                / f"{work_title}_Vol{volume.volume_number}_Ch{ch.chapter_number:03d}.m4a"
            )

            if not ch.translated_text:
                ch_status = "[dim]○ no translation[/dim]"
            elif output_path.exists():
                ch_status = "[green]✓ audio[/green]"
            else:
                ch_status = "[yellow]○ pending[/yellow]"

            console.print(f"    {ch_status} {ch_display}")

        if len(chapters) > 5:
            console.print(f"    [dim]... and {len(chapters) - 5} more chapters[/dim]")

    console.print(
        f"\n[dim]Total: {len(volumes)} volumes, {total_chapters} chapters[/dim]"
    )
    console.print(
        f"[dim]  [green]{total_generated} audio files[/green], {total_pending} pending[/dim]\n"
    )

    return {
        "volumes": len(volumes),
        "chapters": total_chapters,
        "generated": total_generated,
        "pending": total_pending,
    }


def _select_scope_with_context(
    work: Work, volume_repo: VolumeRepository, chapter_repo: ChapterRepository
) -> Optional[str]:
    """Interactive selection of processing scope with context about the work."""
    stats = _display_work_structure(work, volume_repo, chapter_repo)

    if stats["chapters"] == 0:
        console.print("[yellow]No chapters available to generate audio.[/yellow]")
        return None

    choices = []

    if stats["volumes"] > 1 or stats["pending"] > 0:
        pending_desc = f" ({stats['pending']} pending)" if stats["pending"] > 0 else ""
        choices.append(
            questionary.Choice(
                title=f"All Book - Generate audio for all volumes{pending_desc}",
                value=SCOPE_ALL_BOOK,
            )
        )

    if stats["volumes"] >= 1:
        choices.append(
            questionary.Choice(
                title="All Volume - Select a volume to generate audio entirely",
                value=SCOPE_ALL_VOLUME,
            )
        )

    if stats["chapters"] >= 1:
        choices.append(
            questionary.Choice(
                title="Single Chapter - Select a specific chapter",
                value=SCOPE_SINGLE_CHAPTER,
            )
        )

    return questionary.select(
        "Select audio generation scope:",
        choices=choices,
    ).ask()


def _select_volume_interactive(
    work: Work, volume_repo: VolumeRepository
) -> Optional[Volume]:
    """Interactive selection of a volume from a work."""
    if work.id is None:
        console.print("[red]Work has no ID.[/red]")
        return None
    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return None

    volume_choices = [
        questionary.Choice(
            title=f"Volume {v.volume_number}" + (f" - {v.title}" if v.title else ""),
            value=v,
        )
        for v in sorted(volumes, key=lambda vol: vol.volume_number)
    ]

    selected_volume: Optional[Volume] = questionary.select(
        f"Select a volume from '{work.title}':",
        choices=volume_choices,
    ).ask()

    return selected_volume


def _select_chapter_interactive(
    volume: Volume, chapter_repo: ChapterRepository, settings: Settings, work: Work
) -> Optional[Chapter]:
    """Interactive selection of a chapter from a volume."""
    if volume.id is None:
        console.print("[red]Volume has no ID.[/red]")
        return None
    chapters = chapter_repo.get_by_volume(volume.id)
    if not chapters:
        console.print(
            f"[yellow]No chapters found for Volume {volume.volume_number}.[/yellow]"
        )
        return None

    work_title = work.title.replace(" ", "_")

    chapter_choices = []
    for ch in sorted(chapters, key=_get_chapter_sort_key):
        status = ""
        if not ch.translated_text:
            status = " [dim](○ no translation)[/dim]"
        else:
            output_path = (
                settings.paths.audiobooks_dir
                / work_title
                / f"Vol{volume.volume_number}"
                / f"{work_title}_Vol{volume.volume_number}_Ch{ch.chapter_number:03d}.m4a"
            )
            if output_path.exists():
                status = " [green](✓ audio)[/green]"
            else:
                status = " [yellow](○ pending)[/yellow]"

        chapter_choices.append(
            questionary.Choice(
                title=f"{_format_chapter_display(ch)}{status}",
                value=ch,
            )
        )

    selected_chapter: Optional[Chapter] = questionary.select(
        f"Select a chapter from Volume {volume.volume_number}:",
        choices=chapter_choices,
    ).ask()

    return selected_chapter


def _generate_chapter_audio(
    chapter: Chapter,
    volume: Volume,
    work: Work,
    settings: Settings,
) -> bool:
    """Generate audio for a single chapter."""
    if not chapter.translated_text or not chapter.translated_text.strip():
        console.print(f"[yellow]Chapter has no translated text. Skipping.[/yellow]")
        return False

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
            f"[dim]Audio file already exists: {output_filename.name}. Skipping.[/dim]"
        )
        return True

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
                task,
                description=f"[green]✓ Audio saved: {output_filename.name}[/green]",
            )
            return True
        else:
            progress.update(task, description=f"[red]✗ Failed to generate audio[/red]")
            return False


def _generate_volume_audio(
    volume: Volume,
    work: Work,
    settings: Settings,
    chapter_repo: ChapterRepository,
) -> tuple[int, int, int]:
    """Generate audio for all chapters in a volume."""
    chapters = chapter_repo.get_by_volume(volume.id)
    if not chapters:
        console.print(
            f"[yellow]No chapters found in volume {volume.volume_number}[/yellow]"
        )
        return (0, 0, 0)

    console.print(f"[cyan]Generating audio for {len(chapters)} chapters...[/cyan]")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for chapter in chapters:
        result = _generate_chapter_audio(chapter, volume, work, settings)
        if result:
            success_count += 1
        else:
            if not chapter.translated_text:
                skip_count += 1
            else:
                fail_count += 1

    return (success_count, skip_count, fail_count)


def _generate_book_audio(
    work: Work,
    settings: Settings,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
) -> tuple[int, int, int]:
    """Generate audio for all volumes and chapters in a work."""
    if work.id is None:
        console.print("[red]Work has no ID.[/red]")
        return (0, 0, 0)

    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'[/yellow]")
        return (0, 0, 0)

    total_success = 0
    total_skip = 0
    total_fail = 0

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        console.print(f"\n[bold]Volume {volume.volume_number}[/bold]")
        success, skip, fail = _generate_volume_audio(
            volume, work, settings, chapter_repo
        )
        total_success += success
        total_skip += skip
        total_fail += fail

    return (total_success, total_skip, total_fail)


@app.command("generate-audio")
def generate_audio(
    voice: Optional[str] = typer.Option(
        None, "--voice", help="TTS voice (default: from config)"
    ),
):
    """
    Generate audio from translated text in database.

    Interactive command that guides through:
    1. Work selection
    2. Scope selection (All Book / All Volume / Single Chapter)
    3. Volume/Chapter selection as needed
    4. Audio generation

    Examples:
        pdftranslator generate-audio
        pdftranslator generate-audio --voice "Paulina"
    """
    setup_logging()

    work_repo = BookRepository()
    volume_repo = VolumeRepository()
    chapter_repo = ChapterRepository()

    selected_work = _select_work_interactive(work_repo)
    if not selected_work:
        raise typer.Exit(0)

    console.print(Panel.fit(f"[bold blue]{selected_work.title}[/bold blue]"))

    selected_scope = _select_scope_with_context(
        selected_work, volume_repo, chapter_repo
    )
    if not selected_scope:
        raise typer.Exit(0)

    settings = Settings.get()

    total_success = 0
    total_skip = 0
    total_fail = 0

    if selected_scope == SCOPE_ALL_BOOK:
        total_success, total_skip, total_fail = _generate_book_audio(
            selected_work, settings, volume_repo, chapter_repo
        )

    elif selected_scope == SCOPE_ALL_VOLUME:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        total_success, total_skip, total_fail = _generate_volume_audio(
            selected_volume, selected_work, settings, chapter_repo
        )

    elif selected_scope == SCOPE_SINGLE_CHAPTER:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        selected_chapter = _select_chapter_interactive(
            selected_volume, chapter_repo, settings, selected_work
        )
        if not selected_chapter:
            raise typer.Exit(0)

        if selected_chapter.translated_text:
            success = _generate_chapter_audio(
                selected_chapter, selected_volume, selected_work, settings
            )
            total_success = 1 if success else 0
            total_fail = 0 if success else 1
        else:
            console.print("[yellow]Selected chapter has no translated text.[/yellow]")
            total_skip = 1

    # Summary
    console.print()
    console.print(
        f"[cyan]Summary: {total_success} generated, {total_skip} skipped, {total_fail} failed[/cyan]"
    )

    if total_fail > 0:
        raise typer.Exit(1)
