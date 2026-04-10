# PDFTranslator

Document Translation with AI - Translate PDF/EPUB documents using LLM backends with glossary-aware post-processing.

## Features

- **Multi-format support**: PDF, EPUB, DOC, DOCX documents
- **Multiple LLM backends**: NVIDIA, Gemini, Ollama
- **Glossary management**: PostgreSQL with pgvector for semantic search
- **CLI interface**: Beautiful terminal UI with Typer + Rich
- **Web interface**: React frontend with real-time task tracking
- **AI-powered translation**: Context-aware translation with glossary support

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 14+ with pgvector extension

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd PDFTranslator

# Create conda environment
conda env create -f environment.yml
conda activate PDFTranslator

# Set environment variables
export NVIDIA_API_KEY=nvapi-xxx  # For NVIDIA backend
export GOOGLE_API_KEY=xxx        # For Gemini backend
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=pdftranslator
export DB_USER=postgres
export DB_PASSWORD=yourpassword
```

### Running the Application

#### Development Mode (Backend + Frontend)

```bash
# Start both backend and frontend
python PDFAgent.py dev

# With custom host/port
python PDFAgent.py dev --host localhost --port 8080
```

Access the application:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

#### Backend Only

```bash
# Start backend server
python PDFAgent.py backend

# With auto-reload for development
python PDFAgent.py backend --reload

# Custom host/port
python PDFAgent.py backend --host 0.0.0.0 --port 8080
```

#### Frontend Only

```bash
# Start React development server
python PDFAgent.py frontend
```

#### CLI Commands

```bash
# Translate a document
python PDFAgent.py cli translate document.pdf

# Split document into chapters
python PDFAgent.py cli split document.pdf --output ./output

# Show CLI help
python PDFAgent.py cli --help
```

## Project Structure

```
PDFTranslator/
├── src/                    # All source code
│   ├── backend/           # FastAPI backend
│   │   ├── api/          # API routes
│   │   └── main.py       # FastAPI app entry point
│   ├── cli/               # CLI interface (Typer)
│   │   ├── commands/     # CLI commands
│   │   ├── services/     # CLI-specific services
│   │   ├── ui/           # CLI UI components
│   │   ├── app.py        # Typer app
│   │   └── __main__.py   # python -m src.cli
│   ├── core/              # Shared core functionality
│   │   ├── config/       # Configuration (Pydantic Settings)
│   │   ├── models/       # Domain models
│   │   └── exceptions/   # Custom exceptions
│   ├── database/          # Database layer
│   │   ├── repositories/ # Repository pattern
│   │   ├── schemas/      # SQL schemas
│   │   ├── services/     # Database services
│   │   ├── connection.py # Connection pool
│   │   └── models.py     # Data models
│   ├── infrastructure/    # External integrations
│   │   ├── llm/          # LLM implementations (NVIDIA, Gemini, Ollama)
│   │   └── document/     # Document processing (Docling)
│   ├── services/          # Business logic services
│   │   ├── translator.py # Translation service
│   │   └── glossary_translator.py
│   └── tools/             # Utility tools
│       ├── AudioGenerator.py
│       ├── Translator.py
│       └── TextExtractor.py
├── frontend/              # React frontend
│   ├── src/              # React source
│   ├── public/           # Static assets
│   └── package.json
├── tests/                 # Test suite (mirrors src/)
│   ├── backend/
│   ├── cli/
│   ├── core/
│   ├── database/
│   └── infrastructure/
├── docs/                  # Documentation
│   └── plans/            # Design documents
├── PDFAgent.py           # MAIN ENTRY POINT - Multi-mode orchestrator
├── pyproject.toml        # Project configuration
├── README.md
├── CHANGELOG.md
└── AGENTS.md             # Development guidelines
```

## Entry Point - PDFAgent.py

The project uses `PDFAgent.py` as a multi-mode orchestrator built with Typer CLI:

```bash
# Show help
python PDFAgent.py --help

# CLI mode - Run CLI commands
python PDFAgent.py cli translate document.pdf
python PDFAgent.py cli split document.pdf --output ./output

# Backend mode - Start FastAPI backend
python PDFAgent.py backend
python PDFAgent.py backend --host 0.0.0.0 --port 8000
python PDFAgent.py backend --reload  # Development mode with auto-reload

# Frontend mode - Start React frontend
python PDFAgent.py frontend

# Development mode - Start both backend + frontend
python PDFAgent.py dev
python PDFAgent.py dev --host localhost --port 8080
```

### Available Commands

| Command | Description | Options |
|---------|-------------|---------|
| `cli` | Run CLI commands for PDF translation and processing | Pass-through to src.cli.app |
| `backend` | Start FastAPI backend server | `--host, -h`, `--port, -p`, `--reload, -r` |
| `frontend` | Start React frontend development server | Auto-installs npm deps if needed |
| `dev` | Start both backend + frontend for development | `--host, -h`, `--port, -p` |

### Short Flags

- `-h, --host` - Host address to bind (default: 0.0.0.0)
- `-p, --port` - Port number for server (default: 8000)
- `-r, --reload` - Enable auto-reload for backend development

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_nvidia_ai.py

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Run tests in a specific directory
pytest tests/database/

# Run tests matching a pattern
pytest -k "test_chapter"

# Run tests with verbose output
pytest -v

# Run tests with print statements visible
pytest -s
```

### Code Quality

```bash
# Lint with ruff
ruff check .

# Format with ruff
ruff format .

# Type check with mypy
mypy .
```

### Frontend Development

The frontend uses:
- **React 19** with TypeScript
- **Vite 8** for build tooling
- **Tailwind CSS 4** for styling
- **Zustand** for state management
- **Axios** for API calls

Frontend configuration:
- `.env` file controls mock data mode:
  ```
  VITE_USE_MOCK_DATA=true
  VITE_API_BASE_URL=http://localhost:8000/api
  ```
- Set `VITE_USE_MOCK_DATA=false` to connect to real backend

## Architecture

### Backend Stack
- **FastAPI** - Modern Python web framework
- **PostgreSQL + pgvector** - Database with vector similarity search
- **psycopg** with connection pooling - Async database driver
- **Pydantic** - Data validation and settings management
- **Docling** - Document parsing and extraction

### LLM Providers
- **NVIDIA NIM** - NVIDIA's inference microservices
- **Google Gemini** - Google's multimodal AI
- **Ollama** - Local LLM inference

### Configuration
- `Settings` singleton with Pydantic BaseSettings
- Environment variables for secrets
- Per-request temperature override for LLM calls

## Configuration

### Environment Variables

```bash
# LLM API Keys
NVIDIA_API_KEY=nvapi-xxx      # NVIDIA NIM API key
GOOGLE_API_KEY=xxx            # Google Gemini API key

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pdftranslator
DB_USER=postgres
DB_PASSWORD=yourpassword

# LLM Provider Selection
LLM_PROVIDER=nvidia  # Options: nvidia, gemini, ollama
```

### Settings File

Configuration is managed via `src/core/config/settings.py`:

```python
from src.core.config import Settings

settings = Settings.get()
print(settings.agent)  # LLM provider
print(settings.db_host)  # Database host
```

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/your-repo/issues) page.
