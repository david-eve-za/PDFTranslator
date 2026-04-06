# cli/commands/build_glossary.py
import logging
from typing import Optional, List

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

from cli.app import app, console, setup_logging
from database.connection import DatabasePool
from database.models import Work, Volume, Chapter, BuildResult
from database.repositories.book_repository import BookRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.volume_repository import VolumeRepository
from database.services.glossary_manager import GlossaryManager

logger = logging.getLogger(__name__)

# Scope constants
SCOPE_ALL_BOOK = "All Book"
SCOPE_ALL_VOLUME = "All Volume"
SCOPE_SINGLE_CHAPTER = "Single Chapter"


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


def _select_scope() -> Optional[str]:
    """Interactive selection of processing scope."""
    return questionary.select(
        "Select processing scope:",
        choices=[
            questionary.Choice(
                title="All Book (process all volumes, concatenate chapters)",
                value=SCOPE_ALL_BOOK,
            ),
            questionary.Choice(
                title="All Volume (concatenate all chapters of a volume)",
                value=SCOPE_ALL_VOLUME,
            ),
            questionary.Choice(
                title="Single Chapter",
                value=SCOPE_SINGLE_CHAPTER,
            ),
        ],
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
    volume: Volume, chapter_repo: ChapterRepository
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

    chapter_choices = [
        questionary.Choice(
            title=f"Chapter {ch.chapter_number}"
            + (f" - {ch.title}" if ch.title else ""),
            value=ch,
        )
        for ch in sorted(
            chapters,
            key=lambda c: c.chapter_number if c.chapter_number else 0,
        )
    ]

    selected_chapter: Optional[Chapter] = questionary.select(
        f"Select a chapter from Volume {volume.volume_number}:",
        choices=chapter_choices,
    ).ask()

    return selected_chapter


def _concatenate_volume_chapters(
    volume: Volume, chapter_repo: ChapterRepository
) -> str:
    """Concatenate all chapter texts from a volume."""
    if volume.id is None:
        return ""
    chapters = chapter_repo.get_by_volume(volume.id)
    texts = [ch.original_text for ch in chapters if ch.original_text]
    return "\n\n".join(texts)


def _process_all_book(
    selected_work: Work,
    manager: GlossaryManager,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
    source_lang: str,
    target_lang: str,
    dry_run: bool,
    all_entities_by_type: dict,
) -> tuple:
    """Process all volumes in a work, concatenating chapters per volume."""
    if selected_work.id is None:
        console.print("[red]Work has no ID.[/red]")
        return (0, 0, 0)
    volumes = volume_repo.get_by_work_id(selected_work.id)
    if not volumes:
        console.print("[yellow]No volumes found for this work.[/yellow]")
        return (0, 0, 0)

    total_extracted = 0
    total_new = 0
    total_skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        for vol in sorted(volumes, key=lambda v: v.volume_number):
            vol_task = progress.add_task(
                f"[cyan]Processing Volume {vol.volume_number}", total=None
            )

            consolidated_text = _concatenate_volume_chapters(vol, chapter_repo)

            if not consolidated_text:
                progress.update(
                    vol_task, description=f"[dim]Volume {vol.volume_number} (no text)"
                )
                progress.advance(vol_task)
                continue

            progress.update(
                vol_task,
                description=f"[cyan]Volume {vol.volume_number} ({len(consolidated_text)} chars)",
            )

            result = manager.build_from_text(
                text=consolidated_text,
                work_id=selected_work.id,
                source_lang=source_lang,
                target_lang=target_lang,
                suggest_translations=not dry_run,
            )

            total_extracted += result.extracted
            total_new += result.new
            total_skipped += result.skipped

            for etype, count in result.entities_by_type.items():
                all_entities_by_type[etype] = all_entities_by_type.get(etype, 0) + count

            progress.advance(vol_task)

    return (total_extracted, total_new, total_skipped)


def _process_volume_consolidated(
    volume: Volume,
    work_id: int,
    manager: GlossaryManager,
    chapter_repo: ChapterRepository,
    source_lang: str,
    target_lang: str,
    dry_run: bool,
) -> BuildResult:
    """Process a single volume with consolidated chapter text."""
    console.print(
        f"[cyan]Consolidating chapters from Volume {volume.volume_number}...[/cyan]"
    )

    consolidated_text = _concatenate_volume_chapters(volume, chapter_repo)

    if not consolidated_text:
        console.print("[yellow]No text content found in volume.[/yellow]")
        return BuildResult(extracted=0, new=0, skipped=0, entities_by_type={})

    console.print(f"[cyan]Processing {len(consolidated_text)} characters...[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Extracting entities...", total=None)

        result = manager.build_from_text(
            text=consolidated_text,
            work_id=work_id,
            source_lang=source_lang,
            target_lang=target_lang,
            suggest_translations=not dry_run,
        )

        progress.update(task, description="[green]Extraction complete")

    return result


def _print_summary_table(extracted: int, new: int, skipped: int, dry_run: bool):
    """Print summary table with extraction results."""
    table = Table(
        title="Resumen de Extracción", show_header=True, header_style="bold magenta"
    )
    table.add_column("Métrica", style="cyan")
    table.add_column("Cantidad", justify="right", style="green")

    table.add_row("Entidades detectadas", str(extracted))
    table.add_row("Entidades nuevas", str(new))
    table.add_row("Duplicados (ignorados)", str(skipped))
    if dry_run:
        table.add_row("Modo", "[yellow]DRY-RUN (no guardado)[/yellow]")

    console.print()
    console.print(table)


def _print_entity_distribution_chart(entities_by_type: dict):
    """Print bar chart with entity distribution by type."""
    if not entities_by_type:
        return

    console.print("\n[bold]Distribución por tipo de entidad:[/bold]\n")

    max_count = max(entities_by_type.values()) if entities_by_type else 1

    type_labels = {
        "character": "Personajes",
        "place": "Lugares",
        "skill": "Habilidades",
        "item": "Objetos",
        "spell": "Hechizos",
        "faction": "Organizaciones",
        "title": "Títulos",
        "race": "Razas",
        "other": "Otros",
    }

    for etype, count in sorted(entities_by_type.items(), key=lambda x: -x[1]):
        label = type_labels.get(etype, etype)
        bar_width = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_width
        console.print(f" {label:<15} {bar} {count}")


@app.command("build-glossary")
def build_glossary(
    min_frequency: int = typer.Option(
        2, "--min-frequency", "-m", help="Frecuencia mínima de entidades"
    ),
    source_lang: str = typer.Option("en", "--source-lang", "-s", help="Idioma origen"),
    target_lang: str = typer.Option("es", "--target-lang", "-t", help="Idioma destino"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Solo mostrar entidades sin guardar"
    ),
):
    """
    Construye el glosario de traducción extrayendo entidades con NER + RAG.

    El comando guía al usuario a través de selección interactiva:
    1. Selección de obra
    2. Selección de alcance (All Book / All Volume / Single Chapter)
    3. Selección de volumen/capítulo según corresponda

    Ejemplos:
        pdftranslator build-glossary
        pdftranslator build-glossary --min-frequency 3 --dry-run
    """
    setup_logging()

    work_repo = BookRepository()
    volume_repo = VolumeRepository()
    chapter_repo = ChapterRepository()

    selected_work = _select_work_interactive(work_repo)
    if not selected_work:
        raise typer.Exit(0)

    console.print(Panel.fit(f"[bold blue]{selected_work.title}[/bold blue]"))

    selected_scope = _select_scope()
    if not selected_scope:
        raise typer.Exit(0)

    pool = DatabasePool.get_instance()
    manager = GlossaryManager(pool)

    total_extracted = 0
    total_new = 0
    total_skipped = 0
    all_entities_by_type = {}

    if selected_scope == SCOPE_ALL_BOOK:
        total_extracted, total_new, total_skipped = _process_all_book(
            selected_work=selected_work,
            manager=manager,
            volume_repo=volume_repo,
            chapter_repo=chapter_repo,
            source_lang=source_lang,
            target_lang=target_lang,
            dry_run=dry_run,
            all_entities_by_type=all_entities_by_type,
        )

    elif selected_scope == SCOPE_ALL_VOLUME:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        work_id = selected_work.id
        if work_id is None:
            console.print("[red]Work has no ID.[/red]")
            raise typer.Exit(1)

        result = _process_volume_consolidated(
            volume=selected_volume,
            work_id=work_id,
            manager=manager,
            chapter_repo=chapter_repo,
            source_lang=source_lang,
            target_lang=target_lang,
            dry_run=dry_run,
        )

        total_extracted = result.extracted
        total_new = result.new
        total_skipped = result.skipped
        all_entities_by_type = result.entities_by_type

    elif selected_scope == SCOPE_SINGLE_CHAPTER:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        selected_chapter = _select_chapter_interactive(selected_volume, chapter_repo)
        if not selected_chapter:
            raise typer.Exit(0)

        if not selected_chapter.original_text:
            console.print("[yellow]Selected chapter has no text content.[/yellow]")
            raise typer.Exit(0)

        work_id = selected_work.id
        if work_id is None:
            console.print("[red]Work has no ID.[/red]")
            raise typer.Exit(1)

        result = manager.build_from_text(
            text=selected_chapter.original_text,
            work_id=work_id,
            source_lang=source_lang,
            target_lang=target_lang,
            suggest_translations=not dry_run,
        )

        total_extracted = result.extracted
        total_new = result.new
        total_skipped = result.skipped
        all_entities_by_type = result.entities_by_type

    _print_summary_table(total_extracted, total_new, total_skipped, dry_run)
    _print_entity_distribution_chart(all_entities_by_type)

    if dry_run:
        console.print(
            "\n[yellow]Modo dry-run: Los cambios no fueron guardados[/yellow]"
        )
    else:
        console.print(
            f"\n[green]Glosario actualizado: {total_new} nuevas entidades[/green]"
        )
