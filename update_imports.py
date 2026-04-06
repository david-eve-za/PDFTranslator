#!/usr/bin/env python3
"""Script to update imports after directory restructuring.

This script updates all import statements in the src/ directory
to reflect the new package structure.
"""

import os
import re
from pathlib import Path
from typing import Dict, List

IMPORT_MAPPING = {
    "from config.": "from src.core.config.",
    "from config import": "from src.core.config import",
    "import config.": "import src.core.config.",
    "import config": "import src.core.config",
    "from models.": "from src.core.models.",
    "from models import": "from src.core.models import",
    "import models.": "import src.core.models.",
    "from database.": "from src.database.",
    "from database import": "from src.database import",
    "import database.": "import src.database.",
    "from infrastructure.": "from src.infrastructure.",
    "from infrastructure import": "from src.infrastructure import",
    "import infrastructure.": "import src.infrastructure.",
    "from services.": "from src.services.",
    "from services import": "from src.services import",
    "import services.": "import src.services.",
    "from tools.": "from src.tools.",
    "from tools import": "from src.tools import",
    "import tools.": "import src.tools.",
    "from llm.": "from src.infrastructure.llm.",
    "from llm import": "from src.infrastructure.llm import",
    "import llm.": "import src.infrastructure.llm.",
    "from cli.": "from src.cli.",
    "from cli import": "from src.cli import",
    "import cli.": "import src.cli.",
    "from backend.": "from src.backend.",
    "from backend import": "from src.backend import",
    "import backend.": "import src.backend.",
}


def update_imports_in_file(file_path: Path) -> bool:
    """Update imports in a single Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text()
        original_content = content

        for old_import, new_import in IMPORT_MAPPING.items():
            content = content.replace(old_import, new_import)

        if content != original_content:
            file_path.write_text(content)
            print(f"✓ Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory.

    Args:
        directory: Root directory to search

    Returns:
        List of Python file paths
    """
    return list(directory.rglob("*.py"))


def main():
    """Main function to update all imports."""
    src_dir = Path(__file__).parent / "src"

    if not src_dir.exists():
        print(f"Error: {src_dir} does not exist")
        return

    python_files = find_python_files(src_dir)
    print(f"Found {len(python_files)} Python files in {src_dir}")

    modified_count = 0
    for file_path in python_files:
        if update_imports_in_file(file_path):
            modified_count += 1

    print(f"\n✓ Updated {modified_count} files")
    print(f"✗ Skipped {len(python_files) - modified_count} files")


if __name__ == "__main__":
    main()
