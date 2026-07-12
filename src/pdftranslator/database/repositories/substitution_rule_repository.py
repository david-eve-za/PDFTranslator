"""Substitution rule repository for SQLite."""

from typing import Optional, List
from datetime import datetime

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import SubstitutionRule


class SubstitutionRuleRepository(BaseRepository[SubstitutionRule]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from SQLite string format."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # SQLite uses "YYYY-MM-DD HH:MM:SS" format (space), not ISO "T" separator
            # Also handle potential "Z" suffix
            value_str = str(value).strip()
            # Replace space with T for ISO format parsing
            if " " in value_str and "T" not in value_str:
                value_str = value_str.replace(" ", "T")
            if value_str.endswith("Z"):
                value_str = value_str[:-1] + "+00:00"
            return datetime.fromisoformat(value_str)
        except (ValueError, AttributeError):
            return None

    def _row_to_rule(self, row) -> SubstitutionRule:
        return SubstitutionRule(
            id=row["id"],
            name=row["name"],
            pattern=row["pattern"],
            replacement=row["replacement"],
            description=row["description"] if "description" in row.keys() else None,
            is_active=bool(row["is_active"]) if "is_active" in row.keys() else True,
            apply_on_extract=bool(row["apply_on_extract"]) if "apply_on_extract" in row.keys() else True,
            created_at=self._parse_datetime(row["created_at"]) if "created_at" in row.keys() else None,
            updated_at=self._parse_datetime(row["updated_at"]) if "updated_at" in row.keys() else None,
        )

    def get_by_id(self, id: int) -> Optional[SubstitutionRule]:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT * FROM text_substitution_rules WHERE id = ?", (id,))
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_rule(row)

    def get_all(self, active_only: bool = False) -> List[SubstitutionRule]:
        with self._pool.connection() as conn:
            if active_only:
                cur = conn.execute(
                    "SELECT * FROM text_substitution_rules WHERE is_active = 1 ORDER BY name"
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM text_substitution_rules ORDER BY name"
                )
            return [self._row_to_rule(row) for row in cur.fetchall()]

    def get_auto_apply_rules(self) -> List[SubstitutionRule]:
        """Get rules that should be applied on extraction."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM text_substitution_rules
                WHERE is_active = 1 AND apply_on_extract = 1
                ORDER BY name
                """
            )
            return [self._row_to_rule(row) for row in cur.fetchall()]

    def create(self, entity: SubstitutionRule) -> SubstitutionRule:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO text_substitution_rules (name, pattern, replacement, description, is_active, apply_on_extract)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    entity.name,
                    entity.pattern,
                    entity.replacement,
                    entity.description,
                    entity.is_active,
                    entity.apply_on_extract,
                ),
            )
            row = cur.fetchone()
            return self._row_to_rule(row)

    def update(self, entity: SubstitutionRule) -> Optional[SubstitutionRule]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE text_substitution_rules
                SET name = ?, pattern = ?, replacement = ?,
                    description = ?, is_active = ?, apply_on_extract = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                RETURNING *
                """,
                (
                    entity.name,
                    entity.pattern,
                    entity.replacement,
                    entity.description,
                    entity.is_active,
                    entity.apply_on_extract,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            return self._row_to_rule(row) if row else None

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM text_substitution_rules WHERE id = ?", (id,))
            return cur.rowcount > 0