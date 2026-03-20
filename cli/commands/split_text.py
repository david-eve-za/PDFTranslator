import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.panel import Panel

from cli.app import app, console
from database.models import Work, Volume
from database.repositories.book_repository import BookRepository

logger = logging.getLogger(__name__)


def select_volume_interactive(repo: BookRepository) -> Optional[Volume]:
    """
    Interactive selection of a volume from the database.
    Returns the selected Volume or None if cancelled.
    """
    works = repo.find_all()
    if not works:
        console.print("[yellow]No works found in database.[/yellow]")
        return None

    work_choices = [questionary.Choice(title=f"{w.title}", value=w) for w in works]

    selected_work: Optional[Work] = questionary.select(
        "Select a work:",
        choices=work_choices,
    ).ask()

    if not selected_work:
        return None

    volumes = repo.get_volumes(selected_work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{selected_work.title}'.[/yellow]")
        return None

    volume_choices = [
        questionary.Choice(title=f"Volume {v.volume_number}", value=v)
        for v in sorted(volumes, key=lambda vol: vol.volume_number)
    ]

    selected_volume: Optional[Volume] = questionary.select(
        f"Select a volume from '{selected_work.title}':",
        choices=volume_choices,
    ).ask()

    return selected_volume


def open_editor_and_wait(file_path: Path) -> bool:
    """
    Opens the file in the default text editor and waits for it to be closed.
    Returns True if the file was closed successfully, False otherwise.
    """
    try:
        subprocess.run(["open", "-t", str(file_path)], check=True)
        console.print(f"[cyan]Opened editor for: {file_path.name}[/cyan]")
        console.print("[dim]Waiting for editor to close...[/dim]")
        input(
            "[yellow]Press Enter when you have finished editing and closed the editor...[/yellow]"
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open editor: {e}")
        return False
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return False


def update_volume_text(repo: BookRepository, volume_id: int, text: str) -> bool:
    """
    Updates the full_text of a volume in the database.
    Returns True on success, False on failure.
    """
    try:
        volume = repo.get_volume_by_id(volume_id)
        if not volume:
            logger.error(f"Volume with ID {volume_id} not found")
            return False
        volume.full_text = text
        repo.update(volume)
        return True
    except Exception as e:
        logger.error(f"Failed to update volume: {e}")
        return False
