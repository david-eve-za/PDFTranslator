import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

# Configure logging
logger = logging.getLogger(__name__)


# --- Strategy Pattern for Filtering (Open/Closed Principle) ---

class FileFilter(ABC):
    """Abstract base class for a file filtering strategy."""

    @abstractmethod
    def apply(self, file_path: Path) -> bool:
        """
        Applies the filter logic to a given file path.

        Args:
            file_path: The Path object of the file to check.

        Returns:
            True if the file should be included, False otherwise.
        """
        pass


class IsFileFilter(FileFilter):
    """Filter to ensure the path is a file."""

    def apply(self, file_path: Path) -> bool:
        return file_path.is_file()


class ExcludeTranslatedFilter(FileFilter):
    """Filter to exclude files that have been translated (e.g., contain 'translated_')."""

    def apply(self, file_path: Path) -> bool:
        return "translated_" not in file_path.name


# --- Main Class (Single Responsibility & Dependency Inversion) ---

class FilesFinder:
    """
    Finds files in a given directory based on type and a set of filter strategies.
    This class is responsible only for finding and returning file paths.
    """

    def __init__(self, source_path: str):
        """
        Initializes the FilesFinder.

        Args:
            source_path: The path to the directory to search in.

        Raises:
            FileNotFoundError: If the source path does not exist.
            NotADirectoryError: If the source path is not a directory.
        """
        logger.info(f"Initializing FilesFinder with source path: {source_path}")
        self.input_dir = Path(source_path)
        if not self.input_dir.exists():
            logger.error(f"Source path does not exist: {self.input_dir}")
            raise FileNotFoundError(f"Source path does not exist: {self.input_dir}")
        if not self.input_dir.is_dir():
            logger.error(f"Source path is not a directory: {self.input_dir}")
            raise NotADirectoryError(f"Source path is not a directory: {self.input_dir}")

    def get_files(self, file_type: str, filters: List[FileFilter]) -> List[Path]:
        """
        Searches for files recursively, applying a list of filters.

        Args:
            file_type: The extension of the files to search for (e.g., "pdf").
            filters: A list of FileFilter objects to apply.

        Returns:
            A sorted list of Path objects for the files that match the criteria.
        """
        logger.info(f"Searching for *.{file_type} files in: {self.input_dir}")

        # Use rglob to find all files with the given extension.
        candidate_paths = self.input_dir.rglob(f"*.{file_type}")

        # Apply all filters to each path.
        # The class now depends on the FileFilter abstraction, not concrete filters.
        filtered_paths = [
            path for path in candidate_paths if all(f.apply(path) for f in filters)
        ]

        # Path objects are directly sortable.
        sorted_paths = sorted(filtered_paths)

        logger.info(f"Found {len(sorted_paths)} matching .{file_type} files.")
        return sorted_paths
