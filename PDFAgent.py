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
"""

import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
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

# Global state for dev/local mode cleanup
_backend_proc: subprocess.Popen | None = None
_frontend_proc: subprocess.Popen | None = None
_proxy_file: Path | None = None
_shutdown_event = threading.Event()  # Thread-safe flag for shutdown signaling


def _generate_proxy_config(frontend_dir: Path, backend_host: str, backend_port: int) -> Path:
    """Generate dynamic proxy configuration for Angular dev server."""
    config = {
        "/api": {
            "target": f"http://{backend_host}:{backend_port}",
            "secure": False,
            "changeOrigin": True,
            "logLevel": "debug",
        },
        "/health": {
            "target": f"http://{backend_host}:{backend_port}",
            "secure": False,
            "changeOrigin": True,
        },
        "/docs": {
            "target": f"http://{backend_host}:{backend_port}",
            "secure": False,
            "changeOrigin": True,
        },
        "/openapi.json": {
            "target": f"http://{backend_host}:{backend_port}",
            "secure": False,
            "changeOrigin": True,
        },
    }
    # Use .js extension for Angular proxy config (required by @angular/build)
    proxy_file = frontend_dir / "proxy.conf.js.tmp"
    js_content = f"module.exports = {json.dumps(config, indent=2)};"
    proxy_file.write_text(js_content)
    return proxy_file


def _wait_for_backend_ready(host: str, port: int, timeout: float = 30.0) -> bool:
    """Wait for backend health endpoint to respond."""
    url = f"http://{host}:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _kill_process_tree(pid: int) -> None:
    """Kill a process and all its children (for uvicorn reload worker handling)."""
    try:
        import psutil
    except ImportError:
        # Fallback if psutil not available - just kill the parent
        try:
            os.kill(pid, signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)
        except ProcessLookupError:
            pass
        return

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def _terminate_process(proc: subprocess.Popen, name: str, timeout: float = 5.0) -> None:
    """Gracefully terminate a process with timeout, then force kill."""
    if proc is None or proc.poll() is not None:
        return

    logger.info(f"Stopping {name} (PID: {proc.pid})...")

    # Try graceful termination first
    try:
        proc.terminate()
    except ProcessLookupError:
        return

    try:
        proc.wait(timeout=timeout)
        logger.info(f"{name} stopped gracefully")
    except subprocess.TimeoutExpired:
        logger.warning(f"{name} did not stop gracefully, forcing kill...")
        try:
            _kill_process_tree(proc.pid)
        except Exception as e:
            logger.error(f"Error killing {name} process tree: {e}")
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            logger.error(f"Failed to kill {name}")


def _cleanup() -> None:
    """Cleanup processes and temporary files on exit."""
    global _backend_proc, _frontend_proc, _proxy_file

    # Prevent multiple cleanup calls
    if _shutdown_event.is_set():
        return
    _shutdown_event.set()

    _terminate_process(_backend_proc, "backend")
    _terminate_process(_frontend_proc, "frontend")

    if _proxy_file and _proxy_file.exists():
        try:
            _proxy_file.unlink()
            logger.debug(f"Removed proxy config: {_proxy_file}")
        except Exception:
            pass


def _signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals - just set the event, don't call cleanup directly."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    _shutdown_event.set()


# Register signal handlers and atexit
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
atexit.register(_cleanup)


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

        logger.info(f"Starting backend server at http://{host}:{port}")
        uvicorn.run(
            "pdftranslator.backend.main:app",
            host=host,
            port=port,
            reload=reload,
            reload_dirs=["src"] if reload else None,
            log_level="info",
        )
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
    frontend_port: int = typer.Option(
        4200, "--frontend-port", "-fp", help="Port number for frontend server"
    ),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", "-r", help="Enable auto-reload for backend"
    ),
    cors_origins: str = typer.Option(
        "http://localhost,http://localhost:4200,http://localhost:5173,http://localhost:8080,http://10.2.1.119:4200",
        "--cors-origins",
        help="Comma-separated allowed CORS origins",
    ),
) -> None:
    """Start both backend and frontend for development (SQLite database auto-initialized).

    This command starts the FastAPI backend and Angular frontend simultaneously
    for a complete development environment with hot-reload.
    SQLite database is automatically created on first run.

    Examples:
        python PDFAgent.py dev
        python PDFAgent.py dev --port 8080
        python PDFAgent.py dev --host localhost --port 8080 --frontend-port 3000
        python PDFAgent.py dev --no-reload
        python PDFAgent.py dev --cors-origins "http://localhost:4200,http://192.168.1.50:4200"
    """
    global _backend_proc, _frontend_proc, _proxy_file

    logger.info("Starting development mode (backend + frontend)...")

    frontend_dir = Path(__file__).parent / "src" / "pdftranslator" / "frontend"

    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found at {frontend_dir}")
        raise typer.Exit(code=1)

    # Generate dynamic proxy config
    _proxy_file = _generate_proxy_config(frontend_dir, host, port)
    logger.debug(f"Generated proxy config: {_proxy_file}")

    # Environment for backend - set in current process for uvicorn reload subprocess
    db_path = Path(__file__).parent / "data" / "translator.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["SQLITE_PATH"] = str(db_path)

    env = {
        **os.environ,
        "CORS_ORIGINS": cors_origins,
        "SQLITE_PATH": str(db_path),
    }

    # Install frontend dependencies if needed
    if not (frontend_dir / "node_modules").exists():
        logger.warning("node_modules not found. Running npm install...")
        try:
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True, env=env)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            raise typer.Exit(code=1)

    # Start backend as subprocess (required for reload signal handling)
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "pdftranslator.backend.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "info",
    ]
    if reload:
        backend_cmd.extend(["--reload", "--reload-dir", "src"])

    _backend_proc = subprocess.Popen(backend_cmd, env=env)
    # Give backend a moment to start
    time.sleep(1)

    # Wait for backend to be ready with health check
    console.print(f"[blue]Backend:[/blue] Starting on http://{host}:{port} (reload={reload})...")
    with console.status("[bold blue]Waiting for backend to be ready...[/bold blue]") as status:
        ready = _wait_for_backend_ready(host, port, timeout=30.0)
        if ready:
            console.print(f"[green]✓ Backend ready at http://{host}:{port}[/green]")
        else:
            console.print("[red]✗ Backend failed to start within 30 seconds[/red]")
            _cleanup()
            raise typer.Exit(code=1)

    # Start frontend with dynamic proxy config
    console.print(f"[blue]Frontend:[/blue] Starting on http://localhost:{frontend_port}...")
    try:
        _frontend_proc = subprocess.Popen(
            [
                "npm",
                "start",
                "--",
                "--host",
                "0.0.0.0",
                "--port",
                str(frontend_port),
                "--proxy-config",
                str(_proxy_file),
            ],
            cwd=frontend_dir,
            env=env,
        )

        # Monitor both processes without blocking indefinitely
        # This allows signal handlers to work properly
        console.print("[green]✓ Development servers running![/green]")
        console.print("[dim]Press Ctrl+C to stop both servers[/dim]")
        try:
            while True:
                # Check shutdown signal (from SIGINT/SIGTERM)
                if _shutdown_event.is_set():
                    logger.info("Shutdown signal received")
                    break

                # Check if either process has exited unexpectedly
                backend_status = _backend_proc.poll() if _backend_proc else None
                frontend_status = _frontend_proc.poll() if _frontend_proc else None

                if backend_status is not None:
                    logger.error(f"Backend process exited unexpectedly with code {backend_status}")
                    break
                if frontend_status is not None:
                    logger.error(f"Frontend process exited unexpectedly with code {frontend_status}")
                    break

                time.sleep(0.5)  # Check every 500ms

        except KeyboardInterrupt:
            logger.info("Interrupted by user (Ctrl+C)")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start frontend: {e}")
        raise typer.Exit(code=1)
    finally:
        _cleanup()


try:
    from pdftranslator.cli.app import app as cli_app

    app.add_typer(cli_app, name="cli")
except ImportError as e:
    logger.warning(f"CLI commands not available: {e}")

if __name__ == "__main__":
    app()