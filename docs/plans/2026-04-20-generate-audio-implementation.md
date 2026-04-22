# Generate Audio Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add CLI command to generate audio from translated chapters/volumes using AudioGenerator.

**Architecture:** New Typer command with mutual exclusion validation for chapter-id vs volume-id, helper functions for single chapter and volume processing, integration with existing repositories and AudioGenerator.

**Tech Stack:** Typer CLI, Rich progress bars, AudioGenerator (macOS 'say' + ffmpeg), PostgreSQL repositories.

---

## Task 1: Create Test File

**Files:**
- Create: `tests/cli/commands/test_generate_audio.py`

**Step 1: Write the failing test for chapter audio generation**

```python
"""Tests for generate-audio CLI command."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


class TestGenerateAudioCommand:
    """Tests for generate_audio command."""

    def test_generate_audio_for_chapter_success(self, mock_pool):
        """Test successful audio generation for a single chapter."""
        from pdftranslator.cli.commands.generate_audio import generate_audio
        
        # This test will fail until we implement the command
        with pytest.raises(ImportError):
            generate_audio(chapter_id=1, volume_id=None, voice=None)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_generate_audio.py -v`

Expected: FAIL with "cannot import name 'generate_audio'"

**Step 3: Commit test file**

```bash
git add tests/cli/commands/test_generate_audio.py
git commit -m "test: add placeholder test for generate-audio command"
```

---

## Task 2: Create Command File Structure

**Files:**
- Create: `src/pdftranslator/cli/commands/generate_audio.py`

**Step 1: Write basic command structure**

```python
"""Generate audio from translated chapters/volumes."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from pdftranslator.cli.app import console
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.work_repository import WorkRepository
from pdftranslator.tools.AudioGenerator import AudioGenerator

logger = logging.getLogger(__name__)


def generate_audio(
    chapter_id: Optional[int] = typer.Option(
        None, "--chapter-id", "-c", help="Chapter ID to generate audio for"
    ),
    volume_id: Optional[int] = typer.Option(
        None, "--volume-id", "-v", help="Volume ID to generate audio for all chapters"
    ),
    voice: Optional[str] = typer.Option(
        None, "--voice", help="TTS voice (default: from config)"
    ),
) -> None:
    """
    Generate audio from translated text in database.

    Examples:
        python PDFAgent.py generate-audio --chapter-id 123
        python PDFAgent.py generate-audio --volume-id 5
        python PDFAgent.py generate-audio --volume-id 5 --voice "Paulina"
    """
    # Validation: exactly one ID must be provided
    if chapter_id is not None and volume_id is not None:
        console.print("[red]Error: Specify only one of --chapter-id or --volume-id[/red]")
        raise typer.Exit(1)
    
    if chapter_id is None and volume_id is None:
        console.print("[red]Error: Must specify --chapter-id or --volume-id[/red]")
        raise typer.Exit(1)
    
    # Get voice from config if not specified
    settings = Settings.get()
    selected_voice = voice or settings.processing.voice
    
    if chapter_id is not None:
        _generate_chapter_audio(chapter_id, selected_voice)
    else:
        _generate_volume_audio(volume_id, selected_voice)


def _generate_chapter_audio(chapter_id: int, voice: str) -> None:
    """Generate audio for a single chapter."""
    # Placeholder - will implement in next task
    console.print(f"[yellow]Chapter audio generation not yet implemented: chapter_id={chapter_id}[/yellow]")


def _generate_volume_audio(volume_id: int, voice: str) -> None:
    """Generate audio for all chapters in a volume."""
    # Placeholder - will implement in next task
    console.print(f"[yellow]Volume audio generation not yet implemented: volume_id={volume_id}[/yellow]")
```

**Step 2: Run test to verify import works**

Run: `pytest tests/cli/commands/test_generate_audio.py -v`

Expected: PASS (import now works, but functionality not implemented)

**Step 3: Commit basic structure**

```bash
git add src/pdftranslator/cli/commands/generate_audio.py
git commit -m "feat: add generate-audio command structure with validation"
```

---

## Task 3: Implement Chapter Audio Generation

**Files:**
- Modify: `src/pdftranslator/cli/commands/generate_audio.py:67-70`
- Modify: `tests/cli/commands/test_generate_audio.py`

**Step 1: Write test for chapter audio generation**

```python
def test_generate_audio_for_chapter_success(self, mock_pool, tmp_path):
    """Test successful audio generation for a single chapter."""
    from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
    from pdftranslator.core.models.work import Chapter, Volume, Work
    
    # Setup mocks
    mock_chapter_repo = MagicMock(spec=ChapterRepository)
    mock_volume_repo = MagicMock(spec=VolumeRepository)
    mock_work_repo = MagicMock(spec=WorkRepository)
    
    # Create test data
    work = Work(id=1, title="TestWork")
    volume = Volume(id=1, work_id=1, volume_number=1)
    chapter = Chapter(
        id=1,
        volume_id=1,
        chapter_number=3,
        translated_text="This is translated text."
    )
    
    mock_work_repo.get_by_id.return_value = work
    mock_volume_repo.get_by_id.return_value = volume
    mock_chapter_repo.get_by_id.return_value = chapter
    
    # Patch repositories
    with patch('pdftranslator.cli.commands.generate_audio.ChapterRepository', return_value=mock_chapter_repo), \
         patch('pdftranslator.cli.commands.generate_audio.VolumeRepository', return_value=mock_volume_repo), \
         patch('pdftranslator.cli.commands.generate_audio.WorkRepository', return_value=mock_work_repo), \
         patch('pdftranslator.cli.commands.generate_audio.AudioGenerator') as mock_audio_gen:
        
        _generate_chapter_audio(1, "Paulina")
        
        # Verify audio generator was called
        mock_audio_gen.return_value.process_texts.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_generate_audio.py::TestGenerateAudioCommand::test_generate_audio_for_chapter_success -v`

Expected: FAIL (functionality not implemented)

**Step 3: Implement chapter audio generation**

Replace `_generate_chapter_audio` in `src/pdftranslator/cli/commands/generate_audio.py`:

```python
def _generate_chapter_audio(chapter_id: int, voice: str) -> None:
    """Generate audio for a single chapter."""
    pool = DatabasePool.get_instance()
    chapter_repo = ChapterRepository(pool)
    volume_repo = VolumeRepository(pool)
    work_repo = WorkRepository(pool)
    
    # Get chapter
    chapter = chapter_repo.get_by_id(chapter_id)
    if chapter is None:
        console.print(f"[red]Error: Chapter with ID {chapter_id} not found[/red]")
        raise typer.Exit(1)
    
    # Check translated text
    if not chapter.translated_text or not chapter.translated_text.strip():
        console.print(f"[red]Error: Chapter {chapter_id} has no translated text[/red]")
        raise typer.Exit(1)
    
    # Get volume and work for naming
    volume = volume_repo.get_by_id(chapter.volume_id)
    if volume is None:
        console.print(f"[red]Error: Volume with ID {chapter.volume_id} not found[/red]")
        raise typer.Exit(1)
    
    work = work_repo.get_by_id(volume.work_id)
    if work is None:
        console.print(f"[red]Error: Work with ID {volume.work_id} not found[/red]")
        raise typer.Exit(1)
    
    # Build output path
    settings = Settings.get()
    work_title = work.title.replace(" ", "_")
    output_dir = settings.paths.audiobooks_dir / work_title / f"Vol{volume.volume_number}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_filename = output_dir / f"{work_title}_Vol{volume.volume_number}_Ch{chapter.chapter_number:03d}.m4a"
    
    # Check if file exists
    if output_filename.exists():
        console.print(f"[yellow]Audio file already exists: {output_filename}[/yellow]")
        console.print("[yellow]Skipping.[/yellow]")
        return
    
    # Generate audio
    console.print(f"[cyan]Generating audio for Chapter {chapter.chapter_number}...[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating audio...", total=None)
        
        audio_generator = AudioGenerator(progress=progress)
        success = audio_generator.process_texts(
            text_content=chapter.translated_text,
            output_filename=output_filename,
        )
        
        if success:
            progress.update(task, description=f"[green]✓ Audio saved: {output_filename}[/green]")
        else:
            progress.update(task, description=f"[red]✗ Failed to generate audio[/red]")
            raise typer.Exit(1)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/cli/commands/test_generate_audio.py::TestGenerateAudioCommand::test_generate_audio_for_chapter_success -v`

Expected: PASS

**Step 5: Commit chapter implementation**

```bash
git add src/pdftranslator/cli/commands/generate_audio.py tests/cli/commands/test_generate_audio.py
git commit -m "feat: implement chapter audio generation"
```

---

## Task 4: Implement Volume Audio Generation

**Files:**
- Modify: `src/pdftranslator/cli/commands/generate_audio.py:107-110`
- Modify: `tests/cli/commands/test_generate_audio.py`

**Step 1: Write test for volume audio generation**

```python
def test_generate_audio_for_volume_success(self, mock_pool, tmp_path):
    """Test successful audio generation for all chapters in a volume."""
    from pdftranslator.cli.commands.generate_audio import _generate_volume_audio
    from pdftranslator.core.models.work import Chapter, Volume, Work
    
    # Setup mocks
    mock_chapter_repo = MagicMock(spec=ChapterRepository)
    mock_volume_repo = MagicMock(spec=VolumeRepository)
    mock_work_repo = MagicMock(spec=WorkRepository)
    
    # Create test data
    work = Work(id=1, title="TestWork")
    volume = Volume(id=1, work_id=1, volume_number=1)
    chapters = [
        Chapter(id=1, volume_id=1, chapter_number=1, translated_text="Chapter 1 text."),
        Chapter(id=2, volume_id=1, chapter_number=2, translated_text="Chapter 2 text."),
    ]
    
    mock_work_repo.get_by_id.return_value = work
    mock_volume_repo.get_by_id.return_value = volume
    mock_chapter_repo.get_by_volume.return_value = chapters
    
    with patch('pdftranslator.cli.commands.generate_audio.ChapterRepository', return_value=mock_chapter_repo), \
         patch('pdftranslator.cli.commands.generate_audio.VolumeRepository', return_value=mock_volume_repo), \
         patch('pdftranslator.cli.commands.generate_audio.WorkRepository', return_value=mock_work_repo), \
         patch('pdftranslator.cli.commands.generate_audio.AudioGenerator') as mock_audio_gen:
        
        _generate_volume_audio(1, "Paulina")
        
        # Verify audio generator was called for each chapter
        assert mock_audio_gen.return_value.process_texts.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_generate_audio.py::TestGenerateAudioCommand::test_generate_audio_for_volume_success -v`

Expected: FAIL

**Step 3: Implement volume audio generation**

Replace `_generate_volume_audio` in `src/pdftranslator/cli/commands/generate_audio.py`:

```python
def _generate_volume_audio(volume_id: int, voice: str) -> None:
    """Generate audio for all chapters in a volume."""
    pool = DatabasePool.get_instance()
    chapter_repo = ChapterRepository(pool)
    volume_repo = VolumeRepository(pool)
    work_repo = WorkRepository(pool)
    
    # Get volume
    volume = volume_repo.get_by_id(volume_id)
    if volume is None:
        console.print(f"[red]Error: Volume with ID {volume_id} not found[/red]")
        raise typer.Exit(1)
    
    # Get work for naming
    work = work_repo.get_by_id(volume.work_id)
    if work is None:
        console.print(f"[red]Error: Work with ID {volume.work_id} not found[/red]")
        raise typer.Exit(1)
    
    # Get all chapters
    chapters = chapter_repo.get_by_volume(volume_id)
    if not chapters:
        console.print(f"[yellow]No chapters found in volume {volume_id}[/yellow]")
        return
    
    console.print(f"[cyan]Generating audio for {len(chapters)} chapters...[/cyan]")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for chapter in chapters:
        # Check translated text
        if not chapter.translated_text or not chapter.translated_text.strip():
            console.print(f"[yellow]Skipping Chapter {chapter.chapter_number}: no translated text[/yellow]")
            skip_count += 1
            continue
        
        # Build output path
        settings = Settings.get()
        work_title = work.title.replace(" ", "_")
        output_dir = settings.paths.audiobooks_dir / work_title / f"Vol{volume.volume_number}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = output_dir / f"{work_title}_Vol{volume.volume_number}_Ch{chapter.chapter_number:03d}.m4a"
        
        # Check if file exists
        if output_filename.exists():
            console.print(f"[dim]Skipping Chapter {chapter.chapter_number}: file exists[/dim]")
            skip_count += 1
            continue
        
        # Generate audio
        try:
            audio_generator = AudioGenerator()
            success = audio_generator.process_texts(
                text_content=chapter.translated_text,
                output_filename=output_filename,
            )
            
            if success:
                console.print(f"[green]✓ Chapter {chapter.chapter_number}: {output_filename.name}[/green]")
                success_count += 1
            else:
                console.print(f"[red]✗ Chapter {chapter.chapter_number}: generation failed[/red]")
                fail_count += 1
        except Exception as e:
            logger.error(f"Error generating audio for chapter {chapter.id}: {e}")
            console.print(f"[red]✗ Chapter {chapter.chapter_number}: {e}[/red]")
            fail_count += 1
    
    # Summary
    console.print()
    console.print(f"[cyan]Summary: {success_count} succeeded, {skip_count} skipped, {fail_count} failed[/cyan]")
    
    if fail_count > 0:
        raise typer.Exit(1)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/cli/commands/test_generate_audio.py::TestGenerateAudioCommand::test_generate_audio_for_volume_success -v`

Expected: PASS

**Step 5: Commit volume implementation**

```bash
git add src/pdftranslator/cli/commands/generate_audio.py tests/cli/commands/test_generate_audio.py
git commit -m "feat: implement volume audio generation with progress tracking"
```

---

## Task 5: Register Command in CLI

**Files:**
- Modify: `src/pdftranslator/cli/commands/__init__.py`
- Modify: `src/pdftranslator/cli/app.py`

**Step 1: Add import to __init__.py**

Add at end of `src/pdftranslator/cli/commands/__init__.py`:

```python
from pdftranslator.cli.commands.generate_audio import generate_audio

__all__ = [
    "process",
    "add_to_database",
    "split_text",
    "reset_database",
    "build_glossary",
    "translate_chapter",
    "generate_audio",
]
```

**Step 2: Import in app.py**

Add in `src/pdftranslator/cli/app.py` imports section (line 67-74):

```python
from pdftranslator.cli.commands import (
    process,
    add_to_database,
    split_text,
    reset_database,
    build_glossary,
    translate_chapter,
    generate_audio,
)
```

**Step 3: Test command appears in help**

Run: `python PDFAgent.py --help`

Expected: Output includes `generate-audio` command

**Step 4: Commit registration**

```bash
git add src/pdftranslator/cli/commands/__init__.py src/pdftranslator/cli/app.py
git commit -m "feat: register generate-audio command in CLI app"
```

---

## Task 6: Add Error Handling Tests

**Files:**
- Modify: `tests/cli/commands/test_generate_audio.py`

**Step 1: Write error handling tests**

```python
def test_error_both_flags_specified(self):
    """Test error when both chapter-id and volume-id are specified."""
    from pdftranslator.cli.commands.generate_audio import generate_audio
    from typer import Exit
    
    with pytest.raises(Exit):
        generate_audio(chapter_id=1, volume_id=1, voice=None)


def test_error_no_flags_specified(self):
    """Test error when neither chapter-id nor volume-id are specified."""
    from pdftranslator.cli.commands.generate_audio import generate_audio
    from typer import Exit
    
    with pytest.raises(Exit):
        generate_audio(chapter_id=None, volume_id=None, voice=None)


def test_error_chapter_not_found(self, mock_pool):
    """Test error when chapter ID doesn't exist."""
    from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
    from typer import Exit
    
    mock_chapter_repo = MagicMock(spec=ChapterRepository)
    mock_chapter_repo.get_by_id.return_value = None
    
    with patch('pdftranslator.cli.commands.generate_audio.ChapterRepository', return_value=mock_chapter_repo):
        with pytest.raises(Exit):
            _generate_chapter_audio(999, "Paulina")


def test_error_chapter_no_translated_text(self, mock_pool):
    """Test error when chapter has no translated text."""
    from pdftranslator.cli.commands.generate_audio import _generate_chapter_audio
    from pdftranslator.core.models.work import Chapter
    from typer import Exit
    
    mock_chapter_repo = MagicMock(spec=ChapterRepository)
    chapter = Chapter(id=1, volume_id=1, chapter_number=1, translated_text=None)
    mock_chapter_repo.get_by_id.return_value = chapter
    
    with patch('pdftranslator.cli.commands.generate_audio.ChapterRepository', return_value=mock_chapter_repo):
        with pytest.raises(Exit):
            _generate_chapter_audio(1, "Paulina")
```

**Step 2: Run all tests**

Run: `pytest tests/cli/commands/test_generate_audio.py -v`

Expected: All tests PASS

**Step 3: Commit error handling tests**

```bash
git add tests/cli/commands/test_generate_audio.py
git commit -m "test: add error handling tests for generate-audio command"
```

---

## Task 7: Manual Integration Test

**Files:**
- None (manual testing)

**Step 1: Test command help**

Run: `python PDFAgent.py generate-audio --help`

Expected: Shows usage information with all flags

**Step 2: Test error cases**

Run: `python PDFAgent.py generate-audio`

Expected: "Error: Must specify --chapter-id or --volume-id"

Run: `python PDFAgent.py generate-audio -c 1 -v 1`

Expected: "Error: Specify only one of --chapter-id or --volume-id"

**Step 3: Test with real chapter (if database has data)**

Run: `python PDFAgent.py generate-audio --chapter-id 1`

Expected: Generates audio or shows appropriate error message

**Step 4: Final commit**

```bash
git add docs/plans/2026-04-20-generate-audio-command-design.md docs/plans/2026-04-20-generate-audio-implementation.md
git commit -m "docs: add generate-audio implementation plan"
```

---

## Success Criteria Checklist

- [ ] Command appears in `PDFAgent.py --help`
- [ ] `--chapter-id` generates audio for single chapter
- [ ] `--volume-id` generates audio for all chapters in volume
- [ ] Mutual exclusion validation works (only one ID allowed)
- [ ] Progress shown during generation
- [ ] Automatic output directory and filename
- [ ] `--voice` flag overrides config
- [ ] Clear error messages for all failure cases
- [ ] Existing files are skipped with message
- [ ] All unit tests pass
