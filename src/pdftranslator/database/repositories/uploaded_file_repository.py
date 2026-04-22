"""Repository for uploaded files."""

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.models import UploadedFile


class UploadedFileRepository:
    def __init__(self, pool: DatabasePool | None = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_uploaded_file(self, row: tuple) -> UploadedFile:
        return UploadedFile(
            id=row[0],
            filename=row[1],
            original_name=row[2],
            file_path=row[3],
            file_size=row[4],
            file_type=row[5],
            mime_type=row[6],
            work_id=row[7],
            volume_id=row[8],
            status=row[9],
            error_message=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def get_by_id(self, id: int) -> UploadedFile | None:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, original_name, file_path, file_size, file_type,
                       mime_type, work_id, volume_id, status, error_message,
                       created_at, updated_at
                FROM uploaded_files
                WHERE id = %s
                """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_uploaded_file(row)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[UploadedFile]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, original_name, file_path, file_size, file_type,
                       mime_type, work_id, volume_id, status, error_message,
                       created_at, updated_at
                FROM uploaded_files
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
            return [self._row_to_uploaded_file(row) for row in rows]

    def count_all(self) -> int:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM uploaded_files")
            return cur.fetchone()[0]

    def create(self, entity: UploadedFile) -> UploadedFile:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO uploaded_files (
                    filename, original_name, file_path, file_size, file_type,
                    mime_type, work_id, volume_id, status, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE uploaded_files
                SET filename = %s, original_name = %s, file_path = %s, file_size = %s,
                    file_type = %s, mime_type = %s, work_id = %s, volume_id = %s,
                    status = %s, error_message = %s, updated_at = NOW()
                WHERE id = %s
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
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    UPDATE uploaded_files
                    SET status = %s, error_message = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                (status, error_message, id),
            )
            return cur.rowcount > 0

    def update_work_volume(self, id: int, work_id: int, volume_id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE uploaded_files
                SET work_id = %s, volume_id = %s, status = 'completed', updated_at = NOW()
                WHERE id = %s
                """,
                (work_id, volume_id, id),
            )
            return cur.rowcount > 0

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM uploaded_files WHERE id = %s", (id,))
            return cur.rowcount > 0
