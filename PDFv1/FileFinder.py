import os
import logging
from typing import Literal

# Configure logging
logger = logging.getLogger(__name__)


class FilesFinder:
    def __init__(self, source_path: str):
        logger.info(f"Initializing FilesFinder with source path: {source_path}")
        self.input_dir = source_path
        if not os.path.exists(self.input_dir):
            logger.error(f"Source path does not exist: {self.input_dir}")
            raise FileNotFoundError(f"Source path does not exist: {self.input_dir}")

    def get_files(self,file_type: Literal["pdf", "epub"]):
        logger.info(f"Searching for PDF and EPUB files in: {self.input_dir}")
        files = sorted(
            os.path.join(root, file)
            for root, _, files in os.walk(self.input_dir)
            for file in files if file.endswith(f".{file_type}") and "translated_" not in file
        )
        logger.info(f"Found {len(files)} files.")
        return files