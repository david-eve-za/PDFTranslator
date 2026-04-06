import logging
import typer
from rich.console import Console
from rich.panel import Panel
import questionary

from src.cli.app import app, console
from src.core.config.settings import Settings
from src.database.connection import DatabasePool
from src.database.initializer import DatabaseInitializer

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

    Only available when develop_mode is enabled in Settings.
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
        default=False,
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
