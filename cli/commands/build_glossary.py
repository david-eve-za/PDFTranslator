# cli/commands/build_glossary.py
import logging
from typing import Optional

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
from database.repositories.book_repository import BookRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.volume_repository import VolumeRepository
from database.services.glossary_manager import GlossaryManager

logger = logging.getLogger(__name__)


def _get_work_info(work_id: int) -> Optional[dict]:
    """Get work information from database."""
    work_repo = BookRepository()
    work = work_repo.get_by_id(work_id)
    if not work:
        return None
    return {
        "id": work.id,
        "title": work.title,
        "title_translated": work.title_translated,
    }


def _get_volumes_to_process(work_id: int, volume_number: Optional[int]) -> list:
    """Get volumes to process based on filters."""
    volume_repo = VolumeRepository()
    if volume_number:
        volume = volume_repo.get_by_work_and_number(work_id, volume_number)
        return [volume] if volume else []
    return volume_repo.get_by_work(work_id)


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
    work_id: int = typer.Option(..., "--work-id", "-w", help="ID de la obra"),
    volume_number: Optional[int] = typer.Option(
        None, "--volume-number", "-v", help="Número de volumen a procesar"
    ),
    chapter_number: Optional[int] = typer.Option(
        None,
        "--chapter-number",
        "-c",
        help="Número de capítulo (requiere --volume-number)",
    ),
    all_volumes: bool = typer.Option(
        False, "--all", "-a", help="Procesar toda la obra"
    ),
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

    Ejemplos:
        pdftranslator build-glossary -w 1
        pdftranslator build-glossary -w 1 -v 1
        pdftranslator build-glossary -w 1 -v 1 -c 5
        pdftranslator build-glossary -w 1 --all
    """
    setup_logging()

    if chapter_number and not volume_number:
        console.print("[red]Error: --chapter-number requiere --volume-number[/red]")
        raise typer.Exit(1)

    work_info = _get_work_info(work_id)
    if not work_info:
        console.print(f"[red]Obra no encontrada: {work_id}[/red]")
        raise typer.Exit(1)

    title_display = work_info["title"]
    if work_info["title_translated"]:
        title_display += f"\n[dim]({work_info['title_translated']})[/dim]"
    console.print(Panel.fit(f"[bold blue]{title_display}[/bold blue]"))

    pool = DatabasePool.get_instance()
    manager = GlossaryManager(pool)

    volumes = _get_volumes_to_process(work_id, volume_number)
    if not volumes:
        console.print("[yellow]No se encontraron volúmenes para procesar[/yellow]")
        raise typer.Exit(0)

    total_extracted = 0
    total_new = 0
    total_skipped = 0
    all_entities_by_type = {}

    chapter_repo = ChapterRepository()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        for vol in volumes:
            vol_task = progress.add_task(
                f"[cyan]Volumen {vol.volume_number}", total=None
            )
            chapters = chapter_repo.get_by_volume(vol.id)

            if chapter_number:
                chapters = [
                    ch for ch in chapters if ch.chapter_number == chapter_number
                ]

            for ch in chapters:
                ch_label = ch.chapter_number if ch.chapter_number else "Especial"
                progress.update(vol_task, description=f"[cyan]Capítulo {ch_label}")

                if not ch.original_text:
                    continue

                result = manager.build_from_text(
                    text=ch.original_text,
                    work_id=work_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    suggest_translations=not dry_run,
                )

                total_extracted += result.extracted
                total_new += result.new
                total_skipped += result.skipped

                for etype, count in result.entities_by_type.items():
                    all_entities_by_type[etype] = (
                        all_entities_by_type.get(etype, 0) + count
                    )

                progress.advance(vol_task)

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
