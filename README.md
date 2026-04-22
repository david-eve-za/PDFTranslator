# PDFTranslator

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

> **Document Translation & Audiobook Generation with AI**
> 
> A Python application for translating PDF/EPUB documents using LLM backends (NVIDIA, Gemini, Ollama) with intelligent chapter splitting, glossary management, and audiobook generation.

---

## 📖 Table of Contents

- [About The Project](#about-the-project)
  - [Built With](#built-with)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [Web UI](#web-ui)
  - [Examples](#examples)
- [Architecture](#architecture)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---

## 🎯 About The Project

PDFTranslator is a comprehensive document processing tool that combines:

- **Intelligent Document Extraction**: Uses Docling for accurate PDF/EPUB text extraction with structure preservation
- **AI-Powered Translation**: Supports multiple LLM backends (NVIDIA NIM, Google Gemini, Ollama) for high-quality translation
- **Glossary Management**: PostgreSQL with pgvector for terminology consistency across translations
- **Chapter Splitting**: Automatic chapter detection and manual adjustment capabilities
- **Audiobook Generation**: Convert translated documents to audio with customizable voices

### Key Features

✅ **Multi-format Support**: Process PDF, EPUB, DOC, and DOCX files  
✅ **LLM Flexibility**: Switch between NVIDIA, Gemini, and Ollama backends  
✅ **Glossary-Aware Translation**: Consistent terminology using semantic search  
✅ **Parallel Processing**: Handle multiple files efficiently  
✅ **Progress Tracking**: Real-time task status with retry capabilities  
✅ **Web UI**: Modern Angular dashboard for document workflow management  
✅ **CLI Interface**: Powerful terminal commands for automation  

### Built With

**Backend:**
- ![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
- ![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi&logoColor=white)
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue?logo=postgresql&logoColor=white)
- ![pgvector](https://img.shields.io/badge/pgvector-0.2+-orange)
- ![Pydantic](https://img.shields.io/badge/Pydantic-2.0+-red)

**Frontend:**
- ![Angular](https://img.shields.io/badge/Angular-17+-red?logo=angular&logoColor=white)
- ![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript&logoColor=white)
- ![SCSS](https://img.shields.io/badge/SCSS-Styles-pink)
- ![ng2-charts](https://img.shields.io/badge/ng2--charts-Chart.js-orange)

**AI/ML:**
- ![NVIDIA NIM](https://img.shields.io/badge/NVIDIA_NIM-API-green?logo=nvidia&logoColor=white)
- ![Google Gemini](https://img.shields.io/badge/Google_Gemini-API-blue?logo=google&logoColor=white)
- ![Ollama](https://img.shields.io/badge/Ollama-Local-gray?logo=ollama&logoColor=white)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ with pgvector extension
- Node.js 18+ (for web UI)
- API keys for LLM backends (NVIDIA, Google)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PDFTranslator.git
cd PDFTranslator
```

#### 2. Set Up Python Environment

**Using Conda (Recommended):**

```bash
conda env create -f environment.yml
conda activate PDFTranslator
```

**Using pip:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

#### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### Environment Setup

Create a `.env` file in the project root:

```env
# LLM API Keys
NVIDIA_API_KEY=nvapi-xxx
GOOGLE_API_KEY=xxx

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pdftranslator
DB_USER=postgres
DB_PASSWORD=yourpassword

# Frontend Configuration (for development)
VITE_USE_MOCK_DATA=false
VITE_API_BASE_URL=http://localhost:8000/api
```

#### Database Setup

```bash
# Create PostgreSQL database
createdb pdftranslator

# Enable pgvector extension
psql -d pdftranslator -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 💻 Usage

### CLI Commands

#### Process Documents

```bash
# Translate a single file
python PDFAgent.py process /path/to/file.pdf --source-lang en-US --target-lang es-MX

# Process entire directory
python PDFAgent.py process /path/to/directory --agent nvidia

# Generate audiobook
python PDFAgent.py process /path/to/file.pdf --gen-video --voice Paulina
```

#### Manage Glossary

```bash
# Build glossary from existing translations
python PDFAgent.py build-glossary --work-id 1

# Resume from last checkpoint (if interrupted)
python PDFAgent.py build-glossary --work-id 1 --resume

# Force restart (clear all progress)
python PDFAgent.py build-glossary --work-id 1 --force-restart

# Add terms manually
python PDFAgent.py add-to-database --term "arcane" --translation "arcano"
```

### Glossary Build Resume

The glossary build process now supports resuming from interruptions:

```bash
# Normal build
python PDFAgent.py build-glossary --work-id 1

# Resume from last checkpoint (if interrupted)
python PDFAgent.py build-glossary --work-id 1 --resume

# Force restart (clear all progress)
python PDFAgent.py build-glossary --work-id 1 --force-restart
```

**How it works:**
- Progress is saved after each batch (validation, translation)
- Use `--resume` to continue from the exact failure point
- No duplicated LLM calls or processing
- Checkpoints stored in `glossary_build_progress` table

#### Split Chapters

```bash
# Split document into chapters
python PDFAgent.py split-text /path/to/file.pdf
```

#### Database Management

```bash
# Reset database
python PDFAgent.py reset-database --confirm
```

### Web UI

#### Start Backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

#### Start Frontend

```bash
cd frontend
npm run dev
```

Access the web UI at: `http://localhost:5173`

#### Features:

- **Dashboard**: Upload files, view processing status, track task progress, see translation statistics
- **Library**: Browse works with volume/chapter progress indicators, apply substitution rules
- **Split Chapters**: Review and adjust chapter boundaries with interactive marker insertion
- **Glossary**: Manage terminology with AI-powered entity extraction, search, filter, and chart visualization
- **Settings**: Configure LLM providers, database, document processing, and text substitution rules
- **Translate**: View original vs translated text side-by-side

### Split Chapters Feature

The Split Chapters web UI allows you to divide volume text into chapters using an interactive interface:

1. **Select Work & Volume**: Choose a work and volume from your library
2. **Mark Blocks**: Use the interactive editor to insert block markers:
   - `[===Type="Prologue"===]` - Start of a prologue
   - `[===Type="Chapter" Title="Chapter Name"===]` - Start of a chapter
   - `[===Type="Epilogue"===]` - Start of an epilogue
   - `[===End Block===]` - End of any block
3. **Preview**: Preview detected blocks before saving
4. **Process**: Confirm to create chapters in the database

#### API Endpoints

- `POST /api/split/preview` - Preview parsed blocks from text
- `POST /api/split/process` - Process text and create chapters

### Examples

#### Example 1: Translate a PDF

```bash
python PDFAgent.py process book.pdf \
  --source-lang en-US \
  --target-lang es-MX \
  --agent gemini \
  --format mp3
```

#### Example 2: Process Multiple Files

```bash
python PDFAgent.py process ./documents/ \
  --agent nvidia \
  --voice "Paulina"
```

#### Example 3: Create Audiobook

```bash
python PDFAgent.py process novel.epub \
  --gen-video \
  --voice "Daniel" \
  --format m4a
```

---

## 🏗️ Architecture

### Project Structure

```
PDFTranslator/
├── src/pdftranslator/     # Main package
│   ├── backend/           # FastAPI backend
│   │   ├── api/           # API routes and schemas
│   │   └── services/      # Business logic
│   ├── cli/               # CLI commands (Typer)
│   │   ├── commands/      # Individual commands
│   │   └── services/      # CLI-specific services
│   ├── core/              # Shared core
│   │   ├── config/        # Configuration (Pydantic Settings)
│   │   └── models/        # Domain models
│   ├── database/          # Database layer
│   │   ├── repositories/  # Repository pattern
│   │   ├── schemas/       # SQL migrations
│   │   └── services/      # Database services
│   ├── infrastructure/    # External integrations
│   │   ├── llm/           # LLM clients (NVIDIA, Gemini, Ollama)
│   │   └── document/      # Document extractors (Docling)
│   ├── services/          # Business logic
│   └── frontend/          # Angular web application
│       ├── src/
│       │   ├── app/
│       │   │   ├── core/     # Services, models, interceptors
│       │   │   ├── features/ # Feature components
│       │   │   └── shared/   # Shared components
│       │   └── styles.scss   # Global styles & design system
│       └── package.json
├── tests/                 # Test suite (mirrors src/)
├── docs/                  # Documentation
├── PDFAgent.py            # Main entry point / orchestrator
├── pyproject.toml         # Project configuration
├── CHANGELOG.md
├── README.md
└── AGENTS.md
```
PDFTranslator/
├── frontend/              # React web application
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Route pages
│   │   ├── stores/       # Zustand state management
│   │   ├── services/     # API client
│   │   └── types/        # TypeScript definitions
│   └── package.json
│
├── backend/               # FastAPI backend
│   ├── api/
│   │   ├── routes/       # API endpoints
│   │   ├── models/       # Pydantic schemas
│   │   └── services/     # Business logic
│   └── main.py
│
├── cli/                   # CLI commands
│   ├── app.py            # Typer app
│   └── commands/         # Individual commands
│
├── database/              # Database layer
│   ├── models.py         # Data models
│   ├── repositories/     # Repository pattern
│   └── connection.py     # Connection pool
│
├── services/              # Business logic
│   ├── translator.py
│   └── glossary_translator.py
│
├── infrastructure/        # External integrations
│   ├── llm/              # LLM clients
│   └── document/         # Document extractors
│
├── tools/                 # Utilities
│   ├── AudioGenerator.py
│   ├── VideoGenerator.py
│   └── Translator.py
│
└── tests/                 # Test suite
```

### Data Flow

```
Document Upload → Text Extraction → Chapter Splitting
       ↓                                    ↓
   Glossary ←── Terminology Extraction ────┘
       ↓
Translation (LLM) → Overlap Cleaning → Post-Processing
       ↓
Audio Generation → Video (optional) → Output Files
```

### Key Components

#### 1. Document Extraction (`infrastructure/document/`)
- Uses Docling for PDF/EPUB text extraction
- Preserves document structure and formatting
- Extracts images for video generation

#### 2. LLM Integration (`infrastructure/llm/`)
- Protocol-based design for swappable backends
- NVIDIA NIM: High-quality cloud translation
- Google Gemini: Alternative cloud backend
- Ollama: Local model support

#### 3. Glossary System (`database/`)
- PostgreSQL with pgvector for semantic search
- Automatic term extraction and suggestion
- Context-aware translation consistency

#### 4. Translation Pipeline (`services/`)
- Chunk-based processing with overlap handling
- Glossary-aware post-processing
- Error recovery and retry logic

---

## 🛣️ Roadmap

See the [open issues](https://github.com/yourusername/PDFTranslator/issues) for a list of proposed features and known issues.

### Current Phase: Web UI Development

- [x] Frontend project setup (Angular 17+ with standalone components)
- [x] Backend API (FastAPI)
- [x] File upload with drag & drop
- [x] Dashboard with task tracking and charts
- [x] Split Chapters screen
- [x] Glossary management with AI entity extraction
- [x] Settings screen with LLM/database configuration
- [x] Text substitution rules management
- [ ] Translated screen (side-by-side view)
- [ ] Audio generation screen
- [ ] Inline editing capabilities
- [ ] Comprehensive test suite

### Future Enhancements

- [ ] Multi-language support in UI
- [ ] Real-time collaboration
- [ ] Batch processing optimization
- [ ] Custom model fine-tuning
- [ ] Export to various formats
- [ ] Docker deployment
- [ ] Cloud deployment guides

---

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

### How to Contribute

1. **Fork the Project**
   ```bash
   git fork https://github.com/yourusername/PDFTranslator.git
   ```

2. **Create your Feature Branch**
   ```bash
   git checkout -b feature/AmazingFeature
   ```

3. **Commit your Changes**
   ```bash
   git commit -m 'feat: add some amazing feature'
   ```

4. **Push to the Branch**
   ```bash
   git push origin feature/AmazingFeature
   ```

5. **Open a Pull Request**

### Development Guidelines

- Follow the [Code Style Guidelines](AGENTS.md#code-style-guidelines)
- Write tests for new features
- Update documentation
- Ensure all tests pass: `pytest`
- Run linting: `ruff check .`
- Format code: `ruff format .`

### Code Style

- Line length: 88 characters (Black/Ruff default)
- Use double quotes for strings
- Type hints required for all functions
- Follow existing import order: stdlib → third-party → local
- **Frontend**: Use Angular signals for reactive state, SCSS with design system variables
- See `AGENTS.md` for detailed style guidelines and frontend architecture

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📧 Contact

**Project Maintainer**: [Your Name](mailto:your.email@example.com)

**Project Link**: [https://github.com/yourusername/PDFTranslator](https://github.com/yourusername/PDFTranslator)

**Documentation**: [Wiki](https://github.com/yourusername/PDFTranslator/wiki)

**Bug Reports**: [Issues](https://github.com/yourusername/PDFTranslator/issues)

**Feature Requests**: [Discussions](https://github.com/yourusername/PDFTranslator/discussions)

---

## 🙏 Acknowledgments

### Libraries & Frameworks

- **[Docling](https://github.com/DS4SD/docling)** - Advanced document parsing
- **[Typer](https://typer.tiangolo.com/)** - CLI framework with Rich integration
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[Angular](https://angular.dev/)** - Web application framework
- **[Angular Material](https://material.angular.io/)** - UI component library
- **[ng2-charts](https://valor-software.com/ng2-charts/)** - Chart.js wrapper for Angular
- **[pgvector](https://github.com/pgvector/pgvector)** - Vector similarity search

### AI Backends

- **[NVIDIA NIM](https://build.nvidia.com/)** - Enterprise AI inference
- **[Google Gemini](https://ai.google.dev/)** - Multimodal AI
- **[Ollama](https://ollama.ai/)** - Local LLM deployment

### Inspiration

- Document translation workflows
- Audiobook generation pipelines
- AI-assisted content processing

---

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/yourusername/PDFTranslator.svg?style=for-the-badge
[contributors-url]: https://github.com/yourusername/PDFTranslator/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/yourusername/PDFTranslator.svg?style=for-the-badge
[forks-url]: https://github.com/yourusername/PDFTranslator/network/members
[stars-shield]: https://img.shields.io/github/stars/yourusername/PDFTranslator.svg?style=for-the-badge
[stars-url]: https://github.com/yourusername/PDFTranslator/stargazers
[issues-shield]: https://img.shields.io/github/issues/yourusername/PDFTranslator.svg?style=for-the-badge
[issues-url]: https://github.com/yourusername/PDFTranslator/issues
[license-shield]: https://img.shields.io/github/license/yourusername/PDFTranslator.svg?style=for-the-badge
[license-url]: https://github.com/yourusername/PDFTranslator/blob/master/LICENSE
