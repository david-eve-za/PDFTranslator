#!/usr/bin/env python3
"""
PDFTranslator - Multi-mode entry point for document translation with AI.

DEPRECATED: This file is kept for backward compatibility.
For new usage, use one of these methods:

    # Recommended: Use the installed command
    pdftranslator cli translate document.pdf
    pdftranslator backend --port 8080

    # Alternative: Use Python module
    python -m pdftranslator cli translate document.pdf
    python -m pdftranslator backend

This file will delegate to the new pdftranslator package.
"""

import logging
import subprocess
import threading
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(
    name="pdfagent",
    help="PDFTranslator - Document Translation with AI\n\nRun 'python PDFAgent.py cli --help' for CLI commands",
    add_completion=False,
)
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)


@app.command()
def backend(
    host: str = typer.Option(
        "0.0.0.0", "--host", "-h", help="Host address to bind the server"
    ),
    port: int = typer.Option(8000, "--port", "-p", help="Port number for the server"),
    reload: bool = typer.Option(
        False, "--reload", "-r", help="Enable auto-reload for development"
    ),
) -> None:
    """Start FastAPI backend server.

    Examples:
        python PDFAgent.py backend
        python PDFAgent.py backend --port 8080
        python PDFAgent.py backend --host localhost --reload
    """
    try:
        import uvicorn
        from pdftranslator.backend.main import app as fastapi_app

        logger.info(f"Starting backend server at http://{host}:{port}")
        uvicorn.run(fastapi_app, host=host, port=port, reload=reload, log_level="info")
    except ImportError as e:
        logger.error(f"Failed to import backend: {e}")
        logger.error("Make sure you're running from the project root directory")
        raise typer.Exit(code=1)


@app.command()
def frontend() -> None:
    """Start Angular frontend development server.

    Examples:
    python PDFAgent.py frontend
    """
    frontend_dir = Path(__file__).parent / "src" / "pdftranslator" / "frontend"

    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found at {frontend_dir}")
        raise typer.Exit(code=1)

    if not (frontend_dir / "node_modules").exists():
        logger.warning("node_modules not found. Running npm install...")
        try:
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            raise typer.Exit(code=1)

    logger.info("Starting Angular frontend development server...")
    try:
        subprocess.run(["npm", "start"], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start frontend: {e}")
        raise typer.Exit(code=1)


@app.command()
def dev(
    host: str = typer.Option(
        "0.0.0.0", "--host", "-h", help="Host address for backend server"
    ),
    port: int = typer.Option(
        8000, "--port", "-p", help="Port number for backend server"
    ),
) -> None:
    """Start both backend and frontend for development.

    This command starts the FastAPI backend and Angular frontend simultaneously
    for a complete development environment.

    Examples:
    python PDFAgent.py dev
    python PDFAgent.py dev --port 8080
    python PDFAgent.py dev --host localhost --port 3000
    """
    logger.info("Starting development mode (backend + frontend)...")

    def start_backend_thread():
        """Backend thread for dev mode."""
        import uvicorn
        from pdftranslator.backend.main import app as fastapi_app

        uvicorn.run(fastapi_app, host=host, port=port, log_level="info")

    backend_thread = threading.Thread(target=start_backend_thread, daemon=True)
    backend_thread.start()

    logger.info(f"Backend started at http://{host}:{port}")
    console.print(f"[green]Backend:[/green] http://{host}:{port}")
    console.print("[blue]Frontend:[/blue] Starting...")

    frontend_dir = Path(__file__).parent / "src" / "pdftranslator" / "frontend"

    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found at {frontend_dir}")
        raise typer.Exit(code=1)

    if not (frontend_dir / "node_modules").exists():
        logger.warning("node_modules not found. Running npm install...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

    try:
        subprocess.run(["npm", "start"], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start frontend: {e}")
        raise typer.Exit(code=1)


try:
    from pdftranslator.cli.app import app as cli_app

    app.add_typer(cli_app, name="cli")
except ImportError as e:
    logger.warning(f"CLI commands not available: {e}")

if __name__ == "__main__":
    app()
