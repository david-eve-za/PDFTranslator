"""Display components for CLI."""

from rich.console import Console
from rich.table import Table

from pdftranslator.database.models import Work, Volume, Chapter
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository

console = Console()


def display_work_structure(
    work: Work,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
) -> dict:
    """
    Display work structure with translation status.

    Args:
        work: Work to display.
        volume_repo: Volume repository.
        chapter_repo: Chapter repository.

    Returns:
        Dict with volume and chapter counts.
    """
    if work.id is None:
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}

    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}

    total_chapters = 0
    total_translated = 0
    total_pending = 0

    console.print(f"\n[bold]📚 {work.title}[/bold]\n")

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        chapters = chapter_repo.get_by_volume(volume.id) if volume.id else []
        translated = sum(1 for ch in chapters if ch.translated_text)
        pending = len(chapters) - translated

        total_chapters += len(chapters)
        total_translated += translated
        total_pending += pending

        vol_title = f" - {volume.title}" if volume.title else ""
        status = _get_volume_status(translated, len(chapters))

        console.print(
            f"  [cyan]Volume {volume.volume_number}{vol_title}[/cyan]{status}"
        )

        # Show first 5 chapters
        for ch in sorted(chapters, key=_get_chapter_sort_key)[:5]:
            ch_status = "[green]✓[/green]" if ch.translated_text else "[dim]○[/dim]"
            console.print(f"    {ch_status} {_format_chapter_display(ch)}")

        if len(chapters) > 5:
            console.print(f"    [dim]... and {len(chapters) - 5} more chapters[/dim]")

    console.print(
        f"\n[dim]Total: {len(volumes)} volumes, {total_chapters} chapters[/dim]"
    )
    console.print(
        f"[dim]  [green]{total_translated} translated[/green], {total_pending} pending[/dim]\n"
    )

    return {
        "volumes": len(volumes),
        "chapters": total_chapters,
        "translated": total_translated,
        "pending": total_pending,
    }


def print_summary(success: int, failure: int, dry_run: bool = False) -> None:
    """
    Print translation summary table.

    Args:
        success: Number of successful translations.
        failure: Number of failed translations.
        dry_run: Whether this was a dry run.
    """
    table = Table(
        title="Translation Summary", show_header=True, header_style="bold magenta"
    )
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Successfully translated", str(success))
    table.add_row("Failed", str(failure))

    if dry_run:
        table.add_row("Mode", "[yellow]DRY-RUN (no saving)[/yellow]")

    console.print()
    console.print(table)


def _get_volume_status(translated: int, total: int) -> str:
    """Get status string for volume."""
    if translated == total and total > 0:
        return "[green] ✓[/green]"
    elif translated > 0:
        return f"[yellow] ({translated}/{total} translated)[/yellow]"
    elif total > 0:
        return "[dim] (pending)[/dim]"
    return ""


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    """Get sort key for chapter ordering."""
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
    """Format chapter for display."""
    if chapter.chapter_number is None:
        return chapter.title or "Unknown"
    else:
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"
