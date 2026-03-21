# reset-database Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a CLI command to reset the database that is only accessible when develop_mode is enabled in GlobalConfig.

**Architecture:** Add develop_mode attribute to GlobalConfig, create new Typer command in cli/commands/reset_database.py that drops and recreates database tables, registered via import in cli/app.py.

**Tech Stack:** Python, Typer, Rich, Questionary, psycopg_pool, PostgreSQL

---

### Task 1: Add develop_mode to GlobalConfig

**Files:**
- Modify: `GlobalConfig.py`

**Step 1: Add develop_mode attribute**
Add after line 31 (after `self.agent`):
```python
self.develop_mode: bool = False
```

**Step 2: Add to expected types**
Add to `_get_expected_types()` dict (around line 104, after `"agent"`):
```python
"develop_mode": bool,
```

**Step 3: Verify change**
Run: `python -c "from GlobalConfig import GlobalConfig; c = GlobalConfig(); print(c.develop_mode)"`
Expected: `False`

**Step 4: Commit**
```bash
git add GlobalConfig.py
git commit -m "feat: add develop_mode attribute to GlobalConfig"
```

---

### Task 2: Create reset_database command

**Files:**
- Create: `cli/commands/reset_database.py`

**Step 1: Create the command file**
```python
import logging
import typer
from rich.console import Console
from rich.panel import Panel
import questionary

from cli.app import app, console
from GlobalConfig import GlobalConfig
from database.connection import DatabasePool
from database.initializer import DatabaseInitializer

logger = logging.getLogger(__name__)


def _drop_and_recreate_schema(pool):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            conn.commit()
    logger.info("Schema dropped and recreated successfully")


@app.command()
def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    Only available when develop_mode is enabled in GlobalConfig.
    """
    config = GlobalConfig()
    
    if not config.develop_mode:
        console.print(
            Panel.fit(
                "[red]Error: This command is only available in develop mode.[/red]\n"
                "[yellow]Set develop_mode = True in GlobalConfig to enable.[/yellow]"
            )
        )
        raise typer.Exit(1)
    
    console.print(
        Panel.fit(
            "[bold red]⚠ DATABASE RESET[/bold red]\n"
            "[yellow]This will delete ALL data in the database![/yellow]\n"
            "[dim]All tables will be dropped and recreated.[/dim]"
        )
    )
    
    confirm = questionary.confirm(
        "Are you sure you want to reset the database? This cannot be undone.",
        default=False
    ).ask()
    
    if not confirm:
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    
    console.print("[cyan]Resetting database...[/cyan]")
    
    try:
        pool = DatabasePool.get_instance().get_sync_pool()
        
        _drop_and_recreate_schema(pool)
        
        DatabasePool._tables_initialized = False
        DatabaseInitializer().ensure_tables_exist(pool)
        
        console.print("[green]✓ Database reset successfully![/green]")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        console.print(f"[red]✗ Error resetting database: {e}[/red]")
        raise typer.Exit(1)
```

**Step 2: Verify file syntax**
Run: `python -m py_compile cli/commands/reset_database.py`
Expected: No output (success)

**Step 3: Commit**
```bash
git add cli/commands/reset_database.py
git commit -m "feat: add reset-database command"
```

---

### Task 3: Register the command in cli/app.py

**Files:**
- Modify: `cli/app.py`

**Step 1: Add import**
Modify line 67 to include reset_database:
```python
from cli.commands import process, add_to_database, split_text, reset_database
```

**Step 2: Verify command is registered**
Run: `python -m cli --help`
Expected: Output includes `reset-database` in command list

**Step 3: Commit**
```bash
git add cli/app.py
git commit -m "feat: register reset-database command in CLI app"
```

---

### Task 4: Integration Test

**Step 1: Test with develop_mode=False**
Run: `python -m cli reset-database`
Expected: Error message "This command is only available in develop mode"

**Step 2: Test with develop_mode=True (manual)**
1. Set `develop_mode: True` in your config.json
2. Run: `python -m cli reset-database`
3. Decline the confirmation
Expected: "Operation cancelled"

**Step 3: Verify command appears in help**
Run: `python -m cli --help`
Expected: Shows `reset-database` command

**Step 4: Final commit (if any fixes needed)**
```bash
git add -A
git commit -m "fix: resolve any integration issues"
```

---

## Summary

After completion:
- `develop_mode` attribute exists in GlobalConfig (default: False)
- `reset-database` command available via CLI
- Command shows error if develop_mode is False
- Command asks for confirmation before destructive operation
- Command drops and recreates schema, then initializes tables
