# Split Text Block Parsing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extender el comando split-text para parsear bloques estructurados del texto editado, creando Chapters automáticamente basándose en marcadores especiales.

**Architecture:** Añadir componentes de parsing (ParsedBlock, BlockParseError) y funciones para generar plantilla con instrucciones, parsear bloques, y crear chapters en la base de datos.

**Tech Stack:** Python, Regex, Typer, Questionary, PostgreSQL via ChapterRepository

---

## Prerequisites
- Review `cli/commands/split_text.py` for current implementation
- Review `database/repositories/chapter_repository.py` for Chapter creation
- Review design doc: `docs/plans/2026-03-20-split-text-block-parsing-design.md`

---

### Task 1: Add ParsedBlock dataclass and BlockParseError exception

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add imports and exception class**

Add after the existing imports (line 16):

```python
from dataclasses import dataclass
import re

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
```

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add ParsedBlock dataclass and BlockParseError exception"
```

---

### Task 2: Implement build_template_header function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add build_template_header function**

Add after the `BlockParseError` class:

```python
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
```

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add build_template_header function"
```

---

### Task 3: Implement parse_blocks function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add parse_blocks function**

Add after `build_template_header`:

```python
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
                    start_line
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
                    start_line
                )
            
            content = "\n".join(content_lines).strip()
            
            blocks.append(ParsedBlock(
                block_type=block_type,
                title=title,
                content=content,
                start_line=start_line,
                end_line=end_line
            ))
        
        i += 1
    
    return blocks
```

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add parse_blocks function"
```

---

### Task 4: Implement strip_header function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add strip_header function**

Add after `parse_blocks`:

```python
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
```

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add strip_header function"
```

---

### Task 5: Implement validate_and_create_chapters function

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Add import for ChapterRepository**

Add to imports (line 14):

```python
from database.repositories.chapter_repository import ChapterRepository
from database.models import Chapter
```

**Step 2: Add validate_and_create_chapters function**

Add after `strip_header`:

```python
def validate_and_create_chapters(
    volume_id: int, 
    blocks: List[ParsedBlock], 
    chapter_repo: ChapterRepository
) -> int:
    """
    Deletes existing chapters for the volume and creates new ones from parsed blocks.
    Returns the number of chapters created.
    """
    existing_chapters = chapter_repo.get_by_volume(volume_id)
    for chapter in existing_chapters:
        if chapter.id:
            chapter_repo.delete(chapter.id)
    
    chapter_number = 1
    created_count = 0
    
    for block in blocks:
        if block.block_type == "Chapter":
            num = chapter_number
            chapter_number += 1
        else:
            num = None
        
        chapter = Chapter(
            id=None,
            volume_id=volume_id,
            chapter_number=num,
            title=block.title,
            original_text=block.content,
            translated_text=None,
        )
        chapter_repo.create(chapter)
        created_count += 1
    
    return created_count
```

**Step 3: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: add validate_and_create_chapters function"
```

---

### Task 6: Modify split_text command to use new functionality

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Update the split_text command**

Replace the current `split_text()` function (lines 96-157) with:

```python
@app.command()
def split_text():
    """
    Interactively select a volume and edit its text content.
    Opens the text in an external editor with format instructions,
    parses structured blocks, and creates chapters in the database.
    """
    console.print(
        Panel.fit(
            "[bold blue]PDFAgent[/bold blue] - Split Text Editor",
            subtitle="Edit volume text content",
        )
    )

    repo = BookRepository()
    chapter_repo = ChapterRepository()
    
    selected_volume = select_volume_interactive(repo)

    if not selected_volume:
        return

    if not selected_volume.full_text:
        console.print("[red]Error: Selected volume has no text content.[/red]")
        raise typer.Exit(1)

    if not selected_volume.id:
        console.print("[red]Error: Selected volume has no ID.[/red]")
        raise typer.Exit(1)

    temp_dir = Path(tempfile.mkdtemp(prefix="pdfagent_"))
    temp_file = temp_dir / f"volume_{selected_volume.volume_number}_edit.txt"

    try:
        header = build_template_header()
        content_with_header = header + selected_volume.full_text
        
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content_with_header)

        if not open_editor_and_wait(temp_file):
            console.print(
                "[yellow]Editor was not closed properly. Changes not saved.[/yellow]"
            )
            return

        with open(temp_file, "r", encoding="utf-8") as f:
            edited_text = f.read()

        content_without_header = strip_header(edited_text)

        if content_without_header == selected_volume.full_text:
            console.print("[yellow]No changes detected. Database not updated.[/yellow]")
            return

        try:
            blocks = parse_blocks(content_without_header)
        except BlockParseError as e:
            console.print(f"[red]Error parsing blocks:[/red]")
            console.print(f"[red]  {e}[/red]")
            console.print("[yellow]Please fix the format and try again.[/yellow]")
            raise typer.Exit(1)

        if not blocks:
            console.print("[yellow]No blocks found. Only updating volume text.[/yellow]")
            if update_volume_text(repo, selected_volume.id, content_without_header):
                console.print(
                    f"[green]Successfully updated text for Volume {selected_volume.volume_number}[/green]"
                )
            return

        if update_volume_text(repo, selected_volume.id, content_without_header):
            chapters_created = validate_and_create_chapters(
                selected_volume.id, blocks, chapter_repo
            )
            console.print(
                f"[green]Successfully updated Volume {selected_volume.volume_number}[/green]"
            )
            console.print(f"[green]Created {chapters_created} chapter(s)[/green]")
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

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "feat: integrate block parsing into split_text command"
```

---

### Task 7: Add List import

**Files:**
- Modify: `cli/commands/split_text.py`

**Step 1: Update typing imports**

Modify line 6 from:
```python
from typing import Optional
```

to:
```python
from typing import Optional, List
```

**Step 2: Commit**
```bash
git add cli/commands/split_text.py
git commit -m "fix: add List import for type hints"
```

---

### Task 8: Test the command manually

**Step 1: Run the command**
```bash
python -m cli split-text
```

**Step 2: Verify behavior**
- Select a volume with text
- Editor opens with instruction header
- After editing with blocks, parse and create chapters
- Verify chapters created in database

**Step 3: Push if working**
```bash
git push origin main
```

---

## Summary

This implementation extends `split-text` to:
1. Prepend instruction header to volume text
2. Parse structured blocks after editing
3. Validate block format with meaningful errors
4. Create/update chapters in database
5. Handle prologue/epilogue with NULL chapter_number
