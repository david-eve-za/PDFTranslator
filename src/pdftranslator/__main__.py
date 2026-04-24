"""
Entry point for running PDFTranslator as a module.

Usage:
    python -m pdftranslator cli translate document.pdf
    python -m pdftranslator backend
    python -m pdftranslator frontend
"""

import sys
from pathlib import Path


def main():
    """Main entry point for the package."""
    # Check if first argument is 'cli', 'backend', 'frontend', or 'dev'
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "cli":
            # Run CLI commands
            from pdftranslator.cli.app import app as cli_app

            cli_app(sys.argv[2:] if len(sys.argv) > 2 else ["--help"])

        elif command == "backend":
            # Run FastAPI backend
            import uvicorn
            from pdftranslator.backend.main import app as fastapi_app

            # Parse host and port from arguments
            host = "0.0.0.0"
            port = 8000
            reload = False

            for i, arg in enumerate(sys.argv[2:], start=2):
                if arg in ["-h", "--host"] and i + 1 < len(sys.argv):
                    host = sys.argv[i + 1]
                elif arg in ["-p", "--port"] and i + 1 < len(sys.argv):
                    port = int(sys.argv[i + 1])
                elif arg in ["-r", "--reload"]:
                    reload = True

            uvicorn.run(fastapi_app, host=host, port=port, reload=reload)

        elif command == "frontend":
            # Run React frontend
            import subprocess

            frontend_dir = Path(__file__).parent / "frontend"

            if not frontend_dir.exists():
                print("Frontend directory not found")
                sys.exit(1)

            if not (frontend_dir / "node_modules").exists():
                print("Installing frontend dependencies...")
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

            print("Starting frontend development server...")
            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)

        elif command == "dev":
            # Run both backend and frontend
            import threading
            import uvicorn
            from pdftranslator.backend.main import app as fastapi_app

            print("Starting development mode (backend + frontend)...")

            # Start backend in thread
            def start_backend():
                uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info")

            backend_thread = threading.Thread(target=start_backend, daemon=True)
            backend_thread.start()

            print("Backend started at http://0.0.0.0:8000")
            print("Frontend: Starting...")

            # Start frontend
            import subprocess

            frontend_dir = Path(__file__).parent / "frontend"

            if not (frontend_dir / "node_modules").exists():
                print("Installing frontend dependencies...")
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)

        else:
            print(f"Unknown command: {command}")
            print("Available commands: cli, backend, frontend, dev")
            sys.exit(1)
    else:
        # No command provided, show help
        print("PDFTranslator - Document Translation with AI")
        print()
        print("Usage: python -m pdftranslator <command> [options]")
        print()
        print("Commands:")
        print("  cli       Run CLI commands for PDF translation")
        print("  backend   Start FastAPI backend server")
        print("  frontend  Start React frontend development server")
        print("  dev       Start both backend and frontend for development")
        print()
        print("Examples:")
        print("  python -m pdftranslator cli translate document.pdf")
        print("  python -m pdftranslator backend --port 8080")
        print("  python -m pdftranslator dev")


if __name__ == "__main__":
    main()
