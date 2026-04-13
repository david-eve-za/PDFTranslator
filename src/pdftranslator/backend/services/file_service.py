"""File service for handling file uploads and processing."""

import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from pdftranslator.core.config.settings import Settings
from pdftranslator.database.models import UploadedFile, Volume, Work
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.uploaded_file_repository import (
    UploadedFileRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.tools.TextExtractor import TextExtractor

logger = logging.getLogger(__name__)

FILENAME_PATTERN = re.compile(r"^(.+?)\s*-\s*Volume\s+(\d+)$", re.IGNORECASE)

ALLOWED_EXTENSIONS = {".pdf", ".epub", ".doc", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/epub+zip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_MB = 300
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@dataclass
class ParsedFilename:
    title: str
    volume_number: int


@dataclass
class ProcessingResult:
    success: bool
    work_id: int | None = None
    work_title: str | None = None
    volume_id: int | None = None
    volume_number: int | None = None
    error_message: str | None = None


class FileService:
    def __init__(
        self,
        file_repo: UploadedFileRepository | None = None,
        work_repo: BookRepository | None = None,
        volume_repo: VolumeRepository | None = None,
        settings: Settings | None = None,
    ):
        self._file_repo = file_repo or UploadedFileRepository()
        self._work_repo = work_repo or BookRepository()
        self._volume_repo = volume_repo or VolumeRepository()
        self._settings = settings or Settings.get()
        self._extractor = TextExtractor()
        self._upload_dir = self._get_upload_dir()

    def _get_upload_dir(self) -> Path:
        upload_dir = self._settings.paths.base_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    def validate_file(
        self, filename: str, content_type: str | None, size: int
    ) -> tuple[bool, str | None]:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return (
                False,
                f"File extension '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}",
            )

        if content_type and content_type not in ALLOWED_MIME_TYPES:
            return False, f"MIME type '{content_type}' not allowed"

        if size > MAX_FILE_SIZE_BYTES:
            return False, f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"

        return True, None

    def sanitize_filename(self, filename: str) -> str:
        safe_name = os.path.basename(filename)
        safe_name = re.sub(r"[^\w\s\-\.]", "", safe_name)
        safe_name = re.sub(r"\s+", "_", safe_name)
        return safe_name

    def generate_unique_filename(self, original_filename: str) -> str:
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4().hex[:12]
        return f"{unique_id}{ext}"

    async def save_upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str | None,
        source_lang: str | None = None,
        target_lang: str | None = None,
    ) -> UploadedFile:
        unique_filename = self.generate_unique_filename(original_filename)
        file_path = self._upload_dir / unique_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        file_size = len(file_content)
        file_type = Path(original_filename).suffix.lower().lstrip(".")

        uploaded_file = UploadedFile(
            filename=unique_filename,
            original_name=original_filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file_type,
            mime_type=content_type,
            status="uploaded",
        )

        return self._file_repo.create(uploaded_file)

    def parse_filename(self, filename: str) -> ParsedFilename | None:
        stem = Path(filename).stem
        match = FILENAME_PATTERN.match(stem)
        if not match:
            return None
        title = match.group(1).strip()
        volume_number = int(match.group(2))
        return ParsedFilename(title=title, volume_number=volume_number)

    def find_or_create_work(self, parsed: ParsedFilename) -> tuple[Work, bool]:
        existing_works = self._work_repo.find_by_title(parsed.title, fuzzy=False)
        if existing_works:
            return existing_works[0], False

        new_work = Work(
            id=None,
            title=parsed.title,
            title_translated=None,
            source_lang="en",
            target_lang="es",
        )
        created_work = self._work_repo.create(new_work)
        return created_work, True

    def process_file(self, uploaded_file: UploadedFile) -> ProcessingResult:
        if not uploaded_file.file_path:
            return ProcessingResult(success=False, error_message="No file path found")

        file_path = Path(uploaded_file.file_path)

        parsed = self.parse_filename(uploaded_file.original_name)
        if not parsed:
            return ProcessingResult(
                success=False,
                error_message="Could not parse filename. Expected format: 'Title - Volume X'",
            )

        try:
            work, _ = self.find_or_create_work(parsed)

            existing_volumes = self._volume_repo.get_by_work_id(work.id)
            volume_numbers = [v.volume_number for v in existing_volumes]

            if parsed.volume_number in volume_numbers:
                return ProcessingResult(
                    success=False,
                    work_title=work.title,
                    volume_number=parsed.volume_number,
                    error_message=f"Volume {parsed.volume_number} already exists for '{work.title}'",
                )

            text = self._extractor.extract_text(str(file_path))
            if not text:
                return ProcessingResult(
                    success=False,
                    work_title=work.title,
                    volume_number=parsed.volume_number,
                    error_message="Could not extract text from file",
                )

            volume = Volume(
                id=None,
                work_id=work.id,
                volume_number=parsed.volume_number,
                title=None,
                full_text=text,
                translated_text=None,
            )
            created_volume = self._volume_repo.create(volume)

            self._file_repo.update_work_volume(
                uploaded_file.id, work.id, created_volume.id
            )

            self._cleanup_file(file_path)

            self._file_repo.update_status(uploaded_file.id, "done")

            return ProcessingResult(
                success=True,
                work_id=work.id,
                work_title=work.title,
                volume_id=created_volume.id,
                volume_number=parsed.volume_number,
            )

        except Exception as e:
            logger.error(f"Error processing file {uploaded_file.filename}: {e}")
            self._file_repo.update_status(uploaded_file.id, "error", str(e))
            return ProcessingResult(success=False, error_message=str(e))

    def _cleanup_file(self, file_path: Path) -> None:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not cleanup file {file_path}: {e}")

    def get_file(self, file_id: int) -> UploadedFile | None:
        return self._file_repo.get_by_id(file_id)

    def list_files(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[UploadedFile], int]:
        offset = (page - 1) * page_size
        files = self._file_repo.get_all(limit=page_size, offset=offset)
        total = self._file_repo.count_all()
        return files, total

    def delete_file(self, file_id: int) -> bool:
        file = self._file_repo.get_by_id(file_id)
        if not file:
            return False

        if file.file_path:
            self._cleanup_file(Path(file.file_path))

        return self._file_repo.delete(file_id)
