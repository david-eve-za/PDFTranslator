# Split Text Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a CLI command that allows users to interactively select a volume and edit its text content using an external text editor.

**Architecture:** Interactive selection using questionary, temporary file creation for editing with macOS `open` command, and database update after user closes the editor.

**Tech Stack:** Python, Typer, Questionary, SQLite/PostgreSQL via BookRepository

---

## Prerequisites
- Review `cli/commands/add_to_database.py` for questionary usage patterns
- Review `database/repositories/book_repository.py` for available methods
- Review `database/models.py` for Volume structure

---

### Task 1: Create split_text.py module

**Files:**
- Create: `cli/commands/split_text.py`

**Step 1: Write the module skeleton with imports**

```python
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
```

**Step 2: Commit skeleton**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add split_text module skeleton"
```

---

### Task 2: Implement volume selection function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add select_volume_interactive function**

```python
def select_volume_interactive(repo: BookRepository) -> Optional[Volume]:
    """
    Interactive selection of a volume from the database.
    Returns the selected Volume or None if cancelled.
    """
    works = repo.find_all()
    
    if not works:
        console.print("[yellow]No works found in database.[/yellow]")
        return None
    
    work_choices = [
        questionary.Choice(title=f"{w.title}", value=w)
        for w in works
    ]
    
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
```

**Step 2: Commit selection function**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add select_volume_interactive function"
```

---

### Task 3: Implement editor opening and waiting function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add open_editor_and_wait function**

```python
def open_editor_and_wait(file_path: Path) -> bool:
    """
    Opens the file in the default text editor and waits for it to be closed.
    Returns True if the file was closed successfully, False otherwise.
    """
    try:
        subprocess.run(["open", "-t", str(file_path)], check=True)
        console.print(f"[cyan]Opened editor for: {file_path.name}[/cyan]")
        console.print("[dim]Waiting for editor to close...[/dim]")
        
        input("[yellow]Press Enter when you have finished editing and closed the editor...[/yellow]")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open editor: {e}")
        return False
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return False
```

**Step 2: Commit editor function**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add open_editor_and_wait function"
```

---

### Task 4: Implement text update function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add update_volume_text function**

```python
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
```

**Step 2: Commit update function**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add update_volume_text function"
```

---

### Task 5: Implement main command function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add the split_text command**

```python
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
            console.print("[yellow]Editor was not closed properly. Changes not saved.[/yellow]")
            return
        
        with open(temp_file, "r", encoding="utf-8") as f:
            edited_text = f.read()
        
        if edited_text == selected_volume.full_text:
            console.print("[yellow]No changes detected. Database not updated.[/yellow]")
            return
        
        if update_volume_text(repo, selected_volume.id, edited_text):
            console.print(f"[green]Successfully updated text for Volume {selected_volume.volume_number}[/green]")
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
```

**Step 2: Commit main command**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add split_text command implementation"
```

---

### Task 6: Add missing repository methods

**Files:**
- Modify: `database/repositories/book_repository.py`

**Step 1: Check if find_all method exists**
Run: `grep -n "def find_all" database/repositories/book_repository.py`

If not found, add:

```python
def find_all(self) -> List[Work]:
    """Returns all works in the database."""
    with self._get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, title_translated, source_lang, target_lang, author FROM works"
            )
            rows = cursor.fetchall()
            return [
                Work(
                    id=row[0],
                    title=row[1],
                    title_translated=row[2],
                    source_lang=row[3],
                    target_lang=row[4],
                    author=row[5],
                )
                for row in rows
            ]
```

**Step 2: Check if get_volume_by_id method exists**
Run: `grep -n "def get_volume_by_id" database/repositories/book_repository.py`

If not found, add:

```python
def get_volume_by_id(self, volume_id: int) -> Optional[Volume]:
    """Returns a volume by its ID."""
    with self._get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, work_id, volume_number, title, full_text, translated_text FROM volumes WHERE id = %s",
                (volume_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Volume(
                id=row[0],
                work_id=row[1],
                volume_number=row[2],
                title=row[3],
                full_text=row[4],
                translated_text=row[5],
            )
```

**Step 3: Commit repository methods**
```bash
git add database/repositories/book_repository.py
git commit -m "feat: add find_all and get_volume_by_id methods to BookRepository"
```

---

### Task 7: Register command in app.py

**Files:**
- Modify: `cli/app.py`

**Step 1: Add import for split_text command**
At the end of the file, add to the existing imports:

```python
from cli.commands import process, add_to_database, split_text
```

**Step 2: Commit registration**
```bash
git add cli/app.py
git commit -m "feat: register split_text command in CLI app"
```

---

### Task 8: Test the command manually

**Step 1: Run the command**
```bash
python -m cli split-text
```

**Step 2: Verify behavior**
- Interactive selection should work
- Editor should open with volume text
- After closing, changes should be saved
- Temp files should be cleaned up

**Step 3: Commit if working**
```bash
git status
# If all good, no additional commit needed
```

---

## Summary
This implementation creates a fully functional `split-text` command that:
1. Allows interactive selection of Work → Volume
2. Opens the volume text in the default text editor
3. Waits for user to finish editing
4. Saves changes back to the database
5. Cleans up temporary files
