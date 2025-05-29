import logging
from typing import Literal
from pathlib import Path  # Import Path from pathlib

# Configure logging
logger = logging.getLogger(__name__)


class FilesFinder:
    def __init__(self, source_path: str):
        logger.info(f"Initializing FilesFinder with source path: {source_path}")
        self.input_dir = Path(source_path)  # Use Path object for input_dir
        if not self.input_dir.exists():
            logger.error(f"Source path does not exist: {self.input_dir}")
            raise FileNotFoundError(f"Source path does not exist: {self.input_dir}")
        if not self.input_dir.is_dir():  # Add check to ensure it's a directory
            logger.error(f"Source path is not a directory: {self.input_dir}")
            raise NotADirectoryError(f"Source path is not a directory: {self.input_dir}")

    def get_files(self, file_type: Literal["pdf", "epub"]) -> list[str]:  # Added return type hint
        # Log message improved for clarity on what's being searched
        logger.info(f"Searching for non-translated .{file_type} files in: {self.input_dir}")

        found_file_paths = []
        # Use Path.rglob for recursive globbing, which is more direct for this pattern
        # It finds all files matching the extension recursively.
        for path_obj in self.input_dir.rglob(f"*.{file_type}"):
            # Ensure it's a file and apply the filter for "translated_"
            if path_obj.is_file() and "translated_" not in path_obj.name:
                found_file_paths.append(path_obj)

        # Sort the Path objects (they sort based on their string representation)
        # and then convert them to a list of strings.
        sorted_file_strings = sorted([str(p) for p in found_file_paths])

        logger.info(f"Found {len(sorted_file_strings)} .{file_type} files.")
        return sorted_file_strings
