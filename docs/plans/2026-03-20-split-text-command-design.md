# Split Text Command Design

## Overview
Comando CLI que permite al usuario editar manualmente el texto de un volumen, abriendo un editor de texto externo y guardando los cambios en la base de datos.

## Command
- **Name:** `split-text`
- **File:** `cli/commands/split_text.py`
- **Registered in:** `cli/app.py`

## Architecture

### Flow
1. **Selection:** Interactive selection using `questionary` to pick Work → Volume
2. **Get text:** Read `full_text` from selected Volume
3. **Create temp file:** Create `.txt` file in system temp directory
4. **Open editor:** Execute `open -t <file>` (opens default text editor on macOS)
5. **Wait for close:** Poll file or use `os.waitpid` to detect when user closes the file
6. **Read changes:** Get modified content from file
7. **Cleanup:** Delete temp file
8. **Update DB:** Update Volume's `full_text` in database

### Components

#### `select_volume_interactive(repo: BookRepository) -> Optional[Volume]`
- Fetch all Works with their Volumes
- Display hierarchical menu: Work title → Volume number
- Return selected Volume or None if cancelled

#### `open_editor_and_wait(file_path: Path, timeout: int = 3600) -> bool`
- Execute `subprocess.run(["open", "-t", str(file_path)])`
- Wait for file to be closed (polling or file lock detection)
- Return True if closed successfully, False on timeout

#### `update_volume_text(repo: BookRepository, volume_id: int, text: str) -> bool`
- Update Volume's `full_text` field
- Return True on success

### Error Handling
- Volume has no `full_text`: Display error, abort
- Editor timeout: Show message, ask to continue waiting or cancel
- Temp file creation fails: Abort with clear message
- User cancels selection: Exit gracefully

## Implementation Notes
- Use `tempfile.mkdtemp()` for temp directory
- File naming: `{work_title}_volume_{number}_edit.txt`
- No parsing of chapters yet (future enhancement)
- Only updates `full_text`, does not create Chapters

## Dependencies
- `questionary` (already in project)
- `BookRepository` from `database/repositories/book_repository.py`
- `Volume` model from `database/models.py`
