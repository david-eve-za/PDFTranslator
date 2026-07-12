#!/usr/bin/env python3
"""Run database migration for Catalog Service."""

import sqlite3
from pathlib import Path

db_path = Path("src/pdftranslator/services/catalog/data/catalog.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

sql_path = Path("src/pdftranslator/services/catalog/infrastructure/database/migrations/001_catalog_schema.sql")

with open(sql_path) as f:
    sql = f.read()

conn = sqlite3.connect(db_path)
conn.executescript(sql)
conn.commit()

print("✅ Migration complete")
for table in ['works', 'volumes', 'chapters']:
    cursor = conn.execute(f'PRAGMA table_info({table})')
    print(f"\n{table}:")
    for row in cursor.fetchall():
        print(f"  {row}")

# Test insert
conn.execute("INSERT INTO works (uuid, title, source_lang, target_lang, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
             ("test-uuid-1", "Test Book", "en", "es", "2024-01-01T00:00:00", "2024-01-01T00:00:00"))
conn.commit()

work = conn.execute("SELECT * FROM works").fetchone()
print(f"\nTest work inserted: {work}")

conn.close()
print("✅ Database verified - schema works!")