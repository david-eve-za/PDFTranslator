"""Interactive selection components."""

from typing import Optional

import questionary

from src.database.models import Work, Volume, Chapter
from src.database.repositories.book_repository import BookRepository
from src.database.repositories.volume_repository import VolumeRepository
from src.database.repositories.chapter_repository import ChapterRepository


def select_work(repo: BookRepository) -> Optional[Work]:
    """
    Interactive work selection.

    Args:
        repo: Work repository.

    Returns:
        Selected work or None if cancelled.
    """
    works = repo.get_all()
    if not works:
        return None

    choices = [questionary.Choice(title=w.title, value=w) for w in works]
    return questionary.select("Select a work:", choices=choices).ask()


def select_volume(work: Work, repo: VolumeRepository) -> Optional[Volume]:
    """
    Interactive volume selection.

    Args:
        work: Parent work.
        repo: Volume repository.

    Returns:
        Selected volume or None if cancelled.
    """
    if work.id is None:
        return None

    volumes = repo.get_by_work_id(work.id)
    if not volumes:
        return None

    choices = [
        questionary.Choice(
            title=f"Volume {v.volume_number}" + (f" - {v.title}" if v.title else ""),
            value=v,
        )
        for v in sorted(volumes, key=lambda vol: vol.volume_number)
    ]

    return questionary.select(
        f"Select a volume from '{work.title}':",
        choices=choices,
    ).ask()


def select_chapter(
    volume: Volume,
    repo: ChapterRepository,
    show_status: bool = True,
) -> Optional[Chapter]:
    """
    Interactive chapter selection.

    Args:
        volume: Parent volume.
        repo: Chapter repository.
        show_status: Whether to show translation status.

    Returns:
        Selected chapter or None if cancelled.
    """
    if volume.id is None:
        return None

    chapters = repo.get_by_volume(volume.id)
    if not chapters:
        return None

    choices = []
    for ch in sorted(chapters, key=_get_chapter_sort_key):
        status = ""
        if show_status:
            status = (
                " [green](✓ translated)[/green]"
                if ch.translated_text
                else " [dim](○ pending)[/dim]"
            )

        display = f"{_format_chapter_display(ch)}{status}"
        choices.append(questionary.Choice(title=display, value=ch))

    return questionary.select(
        f"Select a chapter from Volume {volume.volume_number}:",
        choices=choices,
    ).ask()


def select_scope() -> Optional[str]:
    """
    Interactive scope selection.

    Returns:
        Selected scope ("all_book", "all_volume", "single_chapter") or None.
    """
    return questionary.select(
        "Select translation scope:",
        choices=[
            questionary.Choice(
                title="All Book (translate all volumes and chapters)", value="all_book"
            ),
            questionary.Choice(
                title="All Volume (translate all chapters of a volume)",
                value="all_volume",
            ),
            questionary.Choice(title="Single Chapter", value="single_chapter"),
        ],
    ).ask()


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
