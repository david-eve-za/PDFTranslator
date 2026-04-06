"""PDFTranslator - Multi-mode entry point for document translation with AI.

Usage:
    python PDFAgent.py cli [command]     # Run CLI commands
    python PDFAgent.py backend           # Start FastAPI backend
    python PDFAgent.py frontend          # Start React frontend
    python PDFAgent.py dev               # Start both backend + frontend
    python PDFAgent.py --help            # Show help

Examples:
    python PDFAgent.py cli translate document.pdf
    python PDFAgent.py cli split document.pdf --output ./output
    python PDFAgent.py backend
    python PDFAgent.py dev
"""

import sys
import subprocess
import argparse
import threading
import logging
from pathlib import Path
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_cli(args: List[str]) -> None:
    """Run CLI commands using Typer application."""
    try:
        from src.cli.app import app

        logger.info("Starting CLI mode...")
        app(args if args else None)
    except ImportError as e:
        logger.error(f"Failed to import CLI: {e}")
        logger.error("Make sure you're running from the project root directory")
        sys.exit(1)


def run_backend(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start FastAPI backend server."""
    try:
        import uvicorn
        from src.backend.main import app

        logger.info(f"Starting backend server at http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except ImportError as e:
        logger.error(f"Failed to import backend: {e}")
        logger.error("Make sure you're running from the project root directory")
        sys.exit(1)


def run_frontend() -> None:
    """Start React frontend development server."""
    frontend_dir = Path(__file__).parent / "frontend"

    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found at {frontend_dir}")
        sys.exit(1)

    if not (frontend_dir / "node_modules").exists():
        logger.warning("node_modules not found. Running npm install...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

    logger.info("Starting frontend development server...")
    try:
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start frontend: {e}")
        sys.exit(1)


def run_dev_mode(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start both backend and frontend for development."""
    logger.info("Starting development mode (backend + frontend)...")

    def start_backend_thread():
        """Backend thread for dev mode."""
        import uvicorn
        from src.backend.main import app

        uvicorn.run(app, host=host, port=port, log_level="info")

    backend_thread = threading.Thread(target=start_backend_thread, daemon=True)
    backend_thread.start()

    logger.info(f"Backend started at http://{host}:{port}")
    logger.info("Starting frontend...")

    run_frontend()


def main() -> None:
    """Main entry point for PDFTranslator orchestrator."""
    parser = argparse.ArgumentParser(
        description="PDFTranslator - Document Translation with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python PDFAgent.py cli translate document.pdf
  python PDFAgent.py cli split document.pdf --output ./output
  python PDFAgent.py backend
  python PDFAgent.py dev
        """,
    )

    parser.add_argument(
        "mode", choices=["cli", "backend", "frontend", "dev"], help="Execution mode"
    )

    parser.add_argument(
        "args", nargs="*", help="Additional arguments for CLI mode or configuration"
    )

    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for backend server (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port", type=int, default=8000, help="Port for backend server (default: 8000)"
    )

    args = parser.parse_args()

    if args.mode == "cli":
        run_cli(args.args)
    elif args.mode == "backend":
        run_backend(host=args.host, port=args.port)
    elif args.mode == "frontend":
        run_frontend()
    elif args.mode == "dev":
        run_dev_mode(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
