import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.panel import Panel

from cli.app import app, console
from database.models import Work, Volume
from database.repositories.book_repository import BookRepository

logger = logging.getLogger(__name__)


@dataclass
class ParsedBlock:
    block_type: str
    title: Optional[str]
    content: str
    start_line: int
    end_line: int


class BlockParseError(Exception):
    def __init__(self, message: str, line_number: int):
        self.message = message
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}")


def build_template_header() -> str:
    """
    Generates the instruction header to be prepended to the volume text.
    This header explains the block format to the user.
    """
    return """# ============================================================
# INSTRUCCIONES DE FORMATO - NO MODIFIQUE ESTA SECCIÓN
# ============================================================
# Use los siguientes marcadores para dividir el texto:
#
# [===Type="Prologue"===]
# Texto del prólogo...
# [===End Block===]
#
# [===Type="Chapter" Title="Nombre opcional"===]
# Texto del capítulo...
# [===End Block===]
#
# [===Type="Epilogue"===]
# Texto del epílogo...
# [===End Block===]
#
# Tipos válidos: Prologue, Chapter, Epilogue
# El atributo Title es opcional
# ============================================================
"""


def parse_blocks(text: str) -> List[ParsedBlock]:
    """
    Parses the text and extracts structured blocks.
    Raises BlockParseError if the format is invalid.
    """
    blocks = []
    lines = text.split("\n")
    start_pattern = re.compile(r'\[===Type="(\w+)"(?:\s+Title="([^"]*)")?===\]')
    end_marker = "[===End Block===]"
    valid_types = {"Prologue", "Chapter", "Epilogue"}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = start_pattern.match(line)
        if match:
            start_line = i + 1
            block_type = match.group(1)
            title = match.group(2)

            if block_type not in valid_types:
                raise BlockParseError(
                    f"Type must be 'Prologue', 'Chapter', or 'Epilogue', got '{block_type}'",
                    start_line,
                )

            content_lines = []
            i += 1
            found_end = False
            while i < len(lines):
                if lines[i].strip() == end_marker:
                    found_end = True
                    end_line = i + 1
                    break
                content_lines.append(lines[i])
                i += 1

            if not found_end:
                raise BlockParseError(
                    f"Block starting at line {start_line} has no matching [===End Block===]",
                    start_line,
                )

            content = "\n".join(content_lines).strip()
            blocks.append(
                ParsedBlock(
                    block_type=block_type,
                    title=title,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        i += 1

    return blocks


def strip_header(text: str) -> str:
    """
    Strips the instruction header from the edited text.
    Returns the text without the header section.
    """
    lines = text.split("\n")
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith("#"):
            content_start = i
            break
        if "============================================================" in line:
            if i + 1 < len(lines):
                content_start = i + 1
                while content_start < len(lines) and lines[content_start].strip() == "":
                    content_start += 1
            break
    return "\n".join(lines[content_start:])


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


@app.command()
def split_text():
    """
    Interactively select a volume and edit its text content.
    Opens the text in an external editor and saves changes to the database.
    """
    console.print(
        Panel.fit(
            "[bold blue]PDFAgent[/bold blue] - Split Text Editor",
            subtitle="Edit volume text content",
        )
    )

    repo = BookRepository()
    selected_volume = select_volume_interactive(repo)

    if not selected_volume:
        return

    if not selected_volume.full_text:
        console.print("[red]Error: Selected volume has no text content.[/red]")
        raise typer.Exit(1)

    temp_dir = Path(tempfile.mkdtemp(prefix="pdfagent_"))
    temp_file = temp_dir / f"volume_{selected_volume.volume_number}_edit.txt"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(selected_volume.full_text)

        if not open_editor_and_wait(temp_file):
            console.print(
                "[yellow]Editor was not closed properly. Changes not saved.[/yellow]"
            )
            return

        with open(temp_file, "r", encoding="utf-8") as f:
            edited_text = f.read()

        if edited_text == selected_volume.full_text:
            console.print("[yellow]No changes detected. Database not updated.[/yellow]")
            return

        if update_volume_text(repo, selected_volume.id, edited_text):
            console.print(
                f"[green]Successfully updated text for Volume {selected_volume.volume_number}[/green]"
            )
        else:
            console.print("[red]Failed to update volume text.[/red]")
            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error during editing: {e}")
        console.print(f"[red]An error occurred: {e}[/red]")
        raise typer.Exit(1)

    finally:
        if temp_file.exists():
            temp_file.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        console.print("[dim]Temporary files cleaned up.[/dim]")
