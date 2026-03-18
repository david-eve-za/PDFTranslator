# Typer + Rich Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate PDFAgent.py from argparse to Typer with Rich for enhanced CLI experience.

**Architecture:** Replace argparse with Typer CLI framework, integrate Rich for colorful output with progress bars and tables. Remove config.json dependency, use CLI arguments only with sensible defaults.

**Tech Stack:** typer[all], rich, pathlib

---

## Task 1: Add typer dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add typer to requirements**
Add line after existing dependencies:
```
typer[all]>=0.9.0
```

**Step 2: Install dependency**
Run: `pip install typer[all]`
Expected: Successfully installed typer, rich, and dependencies

**Step 3: Commit**
```bash
git add requirements.txt
git commit -m "chore: add typer dependency for CLI"
```

---

## Task 2: Simplify GlobalConfig

**Files:**
- Modify: `GlobalConfig.py:168-172`

**Step 1: Remove update_from_args method**
Delete the method `update_from_args` (lines 168-172):
```python
def update_from_args(self, args: Any):
    """Updates configuration from an argparse.Namespace object."""
    for key, value in vars(args).items():
        if hasattr(self, key) and value is not None:
            setattr(self, key, value)
```

**Step 2: Add update_from_dict method**
Add new method after line 172:
```python
def update_from_dict(self, data: dict) -> None:
    """Updates configuration from a dictionary."""
    for key, value in data.items():
        if hasattr(self, key) and value is not None:
            setattr(self, key, value)
```

**Step 3: Commit**
```bash
git add GlobalConfig.py
git commit -m "refactor: replace update_from_args with update_from_dict"
```

---

## Task 3: Migrate PDFAgent.py to Typer

**Files:**
- Modify: `PDFAgent.py`

**Step 1: Update imports**
Replace line 1:
```python
import argparse
```
With:
```python
from pathlib import Path
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.logging import RichHandler
from rich.panel import Panel
```

**Step 2: Initialize typer app and console**
After line 26 (after constants), add:
```python
app = typer.Typer(help="Audiobook Generator from PDF/EPUB with AI Translation")
console = Console()
```

**Step 3: Update setup_logging function**
Replace lines 29-48:
```python
def setup_logging():
    """Configures logging to stream to stdout and a log file."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rich handler for console
    rich_handler = RichHandler(console=console, rich_tracebacks=True)
    rich_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE_NAME)
    file_handler.setFormatter(formatter)
    
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)
```

**Step 4: Replace main function**
Replace lines 294-368 with:
```python
@app.command()
def main(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        help="Path to the directory or file to process",
    ),
    source_lang: str = typer.Option(
        "en-US", "--source-lang", "-sl", help="Source language"
    ),
    target_lang: str = typer.Option(
        "es-MX", "--target-lang", "-tl", help="Target language"
    ),
    output_format: str = typer.Option(
        "m4a", "--format", "-f", 
        help="Final audio file format",
    ),
    voice: str = typer.Option(
        "Paulina", "--voice", help="macOS 'say' voice for the target language"
    ),
    gen_video: bool = typer.Option(
        False, "--gen-video", help="Generate a video"
    ),
    agent: str = typer.Option(
        "nvidia", "--agent", "-a",
        help="The agent for translation (nvidia, gemini, ollama)",
    ),
):
    """
    Orchestrates the process of finding files, extracting text,
    translating, and generating audiobooks.
    """
    setup_logging()
    config = GlobalConfig()
    
    # Update config from CLI arguments
    config.update_from_dict({
        "input_path": str(input_path),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "output_format": output_format,
        "voice": voice,
        "gen_video": gen_video,
        "agent": agent,
    })

    console.print(Panel.fit(
        f"[bold blue]PDFAgent[/bold blue] - Audiobook Generator",
        subtitle=f"Processing: {input_path.name}"
    ))

    services = initialize_services()
    if not services:
        console.print("[red]Error initializing services[/red]")
        raise typer.Exit(1)

    successful_file_count = 0
    failed_file_count = 0

    if input_path.is_file():
        console.print(f"[cyan]Processing single file:[/cyan] {input_path.name}")
        if process_single_file(input_path, services):
            successful_file_count = 1
        else:
            failed_file_count = 1
    elif input_path.is_dir():
        console.print(f"[cyan]Processing directory:[/cyan] {input_path}")
        successful_file_count, failed_file_count = process_files_with_progress(services)
    else:
        console.print(f"[red]Invalid path: {input_path}[/red]")
        raise typer.Exit(1)

    # Print summary table
    print_summary_table(successful_file_count, failed_file_count)


def process_files_with_progress(services: Tuple) -> Tuple[int, int]:
    """Finds and processes all files with a progress bar."""
    config = GlobalConfig()
    file_finder = FileFinder(config.input_path)

    files_to_process: List[Path] = file_finder.get_files(
        file_type=DEFAULT_FILE_TYPE_TO_PROCESS,
        filters=[IsFileFilter(), ExcludeTranslatedFilter()],
    )

    if not files_to_process:
        console.print(
            f"[yellow]No .{DEFAULT_FILE_TYPE_TO_PROCESS} files found in '{config.input_path}'[/yellow]"
        )
        return 0, 0

    console.print(f"[green]Found {len(files_to_process)} files to process[/green]")

    successful_file_count = 0
    failed_file_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing files...", total=len(files_to_process))

        for file_path in files_to_process:
            progress.update(task, description=f"[cyan]Processing: {file_path.name}")
            success = process_single_file(file_path, services)
            if success:
                successful_file_count += 1
            else:
                failed_file_count += 1
            progress.advance(task)

    return successful_file_count, failed_file_count


def print_summary_table(successful: int, failed: int):
    """Prints a summary table with processing results."""
    table = Table(title="Processing Summary", show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    table.add_row("Successfully processed", str(successful))
    table.add_row("Failed", str(failed))
    
    console.print()
    console.print(table)
    console.print(f"\n[dim]Log file: {LOG_FILE_NAME}[/dim]")


if __name__ == "__main__":
    app()
```

**Step 5: Commit**
```bash
git add PDFAgent.py
git commit -m "feat: migrate from argparse to typer with rich"
```

---

## Task 4: Update output_format validation

**Files:**
- Modify: `PDFAgent.py`

**Step 1: Add validation callback**
Add before the `@app.command()` decorator:
```python
def validate_output_format(value: str) -> str:
    valid_formats = {"m4a", "mp3", "aiff", "wav"}
    if value.lower() not in valid_formats:
        raise typer.BadParameter(f"Invalid format. Valid options: {valid_formats}")
    return value.lower()
```

**Step 2: Update output_format option**
Add callback to output_format parameter:
```python
output_format: str = typer.Option(
    "m4a", "--format", "-f",
    help="Final audio file format (m4a, mp3, aiff, wav)",
    callback=validate_output_format,
),
```

**Step 3: Commit**
```bash
git add PDFAgent.py
git commit -m "feat: add output format validation"
```

---

## Task 5: Test the CLI

**Step 1: Test help command**
Run: `python PDFAgent.py --help`
Expected: Show typer formatted help with all options

**Step 2: Test with a valid path**
Run: `python PDFAgent.py --help`
Expected: CLI shows help properly formatted with Rich

**Step 3: Verify imports work**
Run: `python -c "import typer; import rich; print('OK')"`
Expected: OK

---

## Summary of Changes

| File | Change |
|------|--------|
| `requirements.txt` | Add `typer[all]>=0.9.0` |
| `GlobalConfig.py` | Remove `update_from_args`, add `update_from_dict` |
| `PDFAgent.py` | Replace argparse with typer, add Rich progress bars and tables |

## CLI Usage Examples

```bash
# Show help
python PDFAgent.py --help

# Process a single file
python PDFAgent.py /path/to/file.pdf

# Process a directory with custom options
python PDFAgent.py /path/to/dir --source-lang en-US --target-lang es-MX --format mp3

# Generate video
python PDFAgent.py /path/to/file.pdf --gen-video

# Use different agent
python PDFAgent.py /path/to/dir --agent gemini
```
