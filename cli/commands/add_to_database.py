import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import questionary
import typer
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from cli.app import app, console, VALID_EXTENSIONS
from database.models import Work, Volume
from database.repositories.book_repository import BookRepository
from GlobalConfig import GlobalConfig
from tools.TextExtractor import TextExtractor

logger = logging.getLogger(__name__)

FILENAME_PATTERN = re.compile(r"^(.+?)\s*-\s*Volume\s+(\d+)$", re.IGNORECASE)


@dataclass
class ParsedFilename:
    title: str
    volume_number: int


@dataclass
class ProcessingResult:
    filename: str
    success: bool
    work_title: Optional[str] = None
    volume_number: Optional[int] = None
    work_created: bool = False
    error_message: Optional[str] = None


def parse_filename(file_path: Path) -> Optional[ParsedFilename]:
    stem = file_path.stem
    match = FILENAME_PATTERN.match(stem)
    if not match:
        return None
    title = match.group(1).strip()
    volume_number = int(match.group(2))
    return ParsedFilename(title=title, volume_number=volume_number)


def get_book_repository() -> BookRepository:
    config = GlobalConfig()
    return BookRepository(
        host=config.db_host,
        port=config.db_port,
        database=config.db_name,
        user=config.db_user,
        password=config.db_password,
        min_size=config.db_min_pool_size,
        max_size=config.db_max_pool_size,
    )


def find_or_create_work(
    repo: BookRepository, parsed: ParsedFilename
) -> Tuple[Work, bool]:
    existing_works = repo.find_by_title(parsed.title, fuzzy=False)
    if existing_works:
        return existing_works[0], False
    new_work = Work(
        id=None,
        title=parsed.title,
        title_translated=None,
        source_lang="en",
        target_lang="es",
    )
    created_work = repo.create(new_work)
    return created_work, True


def process_single_file(
    file_path: Path,
    repo: BookRepository,
    extractor: TextExtractor,
) -> ProcessingResult:
    parsed = parse_filename(file_path)
    if not parsed:
        return ProcessingResult(
            filename=file_path.name,
            success=False,
            error_message=f"No se pudo parsear el nombre del archivo. Formato esperado: 'Título - Volumen X'",
        )

    try:
        work, work_created = find_or_create_work(repo, parsed)

        existing_volumes = repo.get_volumes(work.id)
        volume_numbers = [v.volume_number for v in existing_volumes]

        if parsed.volume_number in volume_numbers:
            return ProcessingResult(
                filename=file_path.name,
                success=False,
                work_title=work.title,
                volume_number=parsed.volume_number,
                error_message=f"El volumen {parsed.volume_number} ya existe para '{work.title}'",
            )

        text = extractor.extract_text(str(file_path))
        if not text:
            return ProcessingResult(
                filename=file_path.name,
                success=False,
                work_title=work.title,
                volume_number=parsed.volume_number,
                error_message="No se pudo extraer texto del archivo",
            )

        volume = Volume(
            id=None,
            work_id=work.id,
            volume_number=parsed.volume_number,
            title=None,
            full_text=text,
            translated_text=None,
        )
        repo.add_volume(volume)

        return ProcessingResult(
            filename=file_path.name,
            success=True,
            work_title=work.title,
            volume_number=parsed.volume_number,
            work_created=work_created,
        )

    except Exception as e:
        logger.error(f"Error procesando {file_path.name}: {e}", exc_info=True)
        return ProcessingResult(
            filename=file_path.name,
            success=False,
            error_message=str(e),
        )


def process_files(files: List[Path]) -> List[ProcessingResult]:
    results: List[ProcessingResult] = []
    repo = get_book_repository()
    extractor = TextExtractor()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Procesando archivos...", total=len(files))

        for file_path in files:
            progress.update(task, description=f"[cyan]Procesando: {file_path.name}")
            result = process_single_file(file_path, repo, extractor)
            results.append(result)
            progress.advance(task)

    return results


def print_results(results: List[ProcessingResult]) -> None:
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    console.print()

    if successful:
        console.print("[green]✓ Archivos procesados exitosamente:[/green]")
        for r in successful:
            work_status = "Work creado" if r.work_created else "Work existente"
            console.print(
                f"  ✓ [green]'{r.filename}'[/green] → {work_status}, Volumen {r.volume_number}"
            )

    if failed:
        console.print("\n[red]✗ Archivos con errores:[/red]")
        for r in failed:
            console.print(f"  ✗ [red]'{r.filename}'[/red] → {r.error_message}")

    console.print(
        f"\n[dim]Resumen: {len(successful)} exitoso(s), {len(failed)} fallido(s)[/dim]"
    )


def scan_directory_for_files(directory_path: Path) -> List[Path]:
    files = []
    for ext in VALID_EXTENSIONS:
        files.extend(directory_path.rglob(f"*{ext}"))
    return sorted(files)


def handle_single_file(file_path: Path) -> List[Path]:
    if file_path.suffix.lower() not in VALID_EXTENSIONS:
        console.print(
            f"[red]Error: '{file_path.name}' is not a valid PDF or EPUB file.[/red]"
        )
        return []

    confirm = questionary.confirm(
        f'¿Desea añadir "{file_path.name}" a la base de datos?',
        default=False,
    ).ask()

    if confirm:
        return [file_path]
    return []


def handle_directory_selection(directory_path: Path) -> List[Path]:
    files = scan_directory_for_files(directory_path)

    if not files:
        console.print(
            f"[yellow]No se encontraron archivos PDF o EPUB en '{directory_path}'[/yellow]"
        )
        return []

    choices = [questionary.Choice(title=f.name, value=f) for f in files]

    selected = questionary.checkbox(
        "Seleccione los archivos a añadir a la base de datos:",
        choices=choices,
        instruction="\n Use las flechas para navegar, Espacio para seleccionar, Enter para confirmar",
    ).ask()

    return selected if selected else []


@app.command()
def add_to_database(
    path: Path = typer.Argument(
        ...,
        exists=True,
        help="Ruta al archivo o carpeta a procesar",
    ),
):
    """
    Explora una ruta y permite seleccionar archivos PDF/EPUB para añadir a la base de datos.
    Extrae el texto y asocia cada archivo con su libro y volumen correspondientes.
    """
    console.print(
        Panel.fit(
            "[bold blue]PDFAgent[/bold blue] - Add to Database",
            subtitle=f"Explorando: {path.name}",
        )
    )

    selected_files = []

    if path.is_file():
        console.print(f"[cyan]Archivo detectado:[/cyan] {path.name}")
        selected_files = handle_single_file(path)
    elif path.is_dir():
        console.print(f"[cyan]Carpeta detectada:[/cyan] {path}")
        selected_files = handle_directory_selection(path)
    else:
        console.print(f"[red]Ruta inválida: {path}[/red]")
        raise typer.Exit(1)

    if not selected_files:
        console.print("\n[yellow]No se seleccionaron archivos.[/yellow]")
        return

    console.print(f"\n[cyan]Procesando {len(selected_files)} archivo(s)...[/cyan]")

    results = process_files(selected_files)
    print_results(results)
