import logging

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

import warnings

warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*pkg_resources is deprecated.*"
)

LOG_FILE_NAME = "PDFAgent.log"
DEFAULT_OUTPUT_SUBDIR = "audiobooks"
DEFAULT_FILE_TYPE_TO_PROCESS = "pdf"
VALID_EXTENSIONS = {".pdf", ".epub"}

app = typer.Typer(help="Audiobook Generator from PDF/EPUB with AI Translation")
console = Console()


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rich_handler = RichHandler(console=console, rich_tracebacks=True)
    rich_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE_NAME)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)


def print_summary_table(successful: int, failed: int):
    table = Table(
        title="Processing Summary", show_header=True, header_style="bold magenta"
    )
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Successfully processed", str(successful))
    table.add_row("Failed", str(failed))

    console.print()
    console.print(table)
    console.print(f"\n[dim]Log file: {LOG_FILE_NAME}[/dim]")


def validate_output_format(value: str) -> str:
    valid_formats = {"m4a", "mp3", "aiff", "wav"}
    if value.lower() not in valid_formats:
        raise typer.BadParameter(f"Invalid format. Valid options: {valid_formats}")
    return value.lower()


from cli.commands import process, add_to_database, split_text
