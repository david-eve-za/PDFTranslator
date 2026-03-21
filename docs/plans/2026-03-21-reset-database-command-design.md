# Design: reset-database Command

## Overview
Add a CLI command to reset the database (drop and recreate tables). The command is only accessible when `develop_mode = True` in GlobalConfig.

## Requirements
- Command visible only when `develop_mode = True`
- Drops all tables with CASCADE
- Recreates tables from schema SQL files
- Requires user confirmation before execution
- Uses existing infrastructure (DatabasePool, DatabaseInitializer)

## Design

### 1. GlobalConfig.py Modifications
Add new attribute:
```python
develop_mode: bool = False
```
Update `_get_expected_types()` to include validation.

### 2. New Command: cli/commands/reset_database.py
Location: `cli/commands/reset_database.py`

Flow:
1. Check `GlobalConfig().develop_mode`
   - If False: show error "Command only available in develop mode" and exit
2. Show confirmation dialog using `questionary.confirm()`
   - If declined: show "Operation cancelled" and exit
3. Execute reset:
   - Connect to database
   - Execute `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
   - Call `DatabaseInitializer.ensure_tables_exist()`
4. Show success/error message

### 3. Update cli/app.py
Add import:
```python
from cli.commands import reset_database
```

### 4. DatabasePool Reset
Add method or flag reset for `_tables_initialized` to force re-initialization.

## Files to Modify/Create
- `GlobalConfig.py` - add develop_mode attribute
- `cli/commands/reset_database.py` - new file (command implementation)
- `cli/app.py` - add import for new command

## Security
- develop_mode defaults to False (production safe)
- Explicit user confirmation required
- Clear warning messages before destructive operation
