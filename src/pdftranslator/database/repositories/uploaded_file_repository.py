"""Repository for uploaded files."""

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.models import UploadedFile


class UploadedFileRepository:
    def __init__(self, pool: DatabasePool | None = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_uploaded_file(self, row) -> UploadedFile:
        return UploadedFile(
            id=row["id"],
            filename=row["filename"],
            original_name=row["original_name"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            file_type=row["file_type"],
            mime_type=row["mime_type"],
            work_id=row["work_id"],
            volume_id=row["volume_id"],
            status=row["status"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_id(self, id: int) -> UploadedFile | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, filename, original_name, file_path, file_size, file_type,
                       mime_type, work_id, volume_id, status, error_message,
                       created_at, updated_at
                FROM uploaded_files
                WHERE id = ?
                """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_uploaded_file(row)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[UploadedFile]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, filename, original_name, file_path, file_size, file_type,
                       mime_type, work_id, volume_id, status, error_message,
                       created_at, updated_at
                FROM uploaded_files
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
            return [self._row_to_uploaded_file(row) for row in rows]

    def count_all(self) -> int:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM uploaded_files")
            row = cur.fetchone()
            return row[0] if row else 0

    def create(self, entity: UploadedFile) -> UploadedFile:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO uploaded_files (
                    filename, original_name, file_path, file_size, file_type,
                    mime_type, work_id, volume_id, status, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id, filename, original_name, file_path, file_size, file_type,
                          mime_type, work_id, volume_id, status, error_message,
                          created_at, updated_at
                """,
                (
                    entity.filename,
                    entity.original_name,
                    entity.file_path,
                    entity.file_size,
                    entity.file_type,
                    entity.mime_type,
                    entity.work_id,
                    entity.volume_id,
                    entity.status,
                    entity.error_message,
                ),
            )
            row = cur.fetchone()
            return self._row_to_uploaded_file(row)

    def update(self, entity: UploadedFile) -> UploadedFile | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE uploaded_files
                SET filename = ?, original_name = ?, file_path = ?, file_size = ?,
                    file_type = ?, mime_type = ?, work_id = ?, volume_id = ?,
                    status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                RETURNING id, filename, original_name, file_path, file_size, file_type,
                          mime_type, work_id, volume_id, status, error_message,
                          created_at, updated_at
                """,
                (
                    entity.filename,
                    entity.original_name,
                    entity.file_path,
                    entity.file_size,
                    entity.file_type,
                    entity.mime_type,
                    entity.work_id,
                    entity.volume_id,
                    entity.status,
                    entity.error_message,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_uploaded_file(row)

    def update_status(
        self, id: int, status: str, error_message: str | None = None
    ) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE uploaded_files
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, error_message, id),
            )
            return cur.rowcount > 0

    def update_work_volume(self, id: int, work_id: int, volume_id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE uploaded_files
                SET work_id = ?, volume_id = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (work_id, volume_id, id),
            )
            return cur.rowcount > 0

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM uploaded_files WHERE id = ?", (id,))
            return cur.rowcount > 0