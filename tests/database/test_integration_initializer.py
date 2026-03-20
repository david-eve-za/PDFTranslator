import os
import pytest
from psycopg_pool import ConnectionPool
from database.initializer import DatabaseInitializer


pytestmark = pytest.mark.integration


def get_test_db_config():
    return {
        "host": os.environ.get("TEST_DB_HOST", "localhost"),
        "port": int(os.environ.get("TEST_DB_PORT", "5432")),
        "database": os.environ.get("TEST_DB_NAME", "test_pdftranslator"),
        "user": os.environ.get("TEST_DB_USER", "postgres"),
        "password": os.environ.get("TEST_DB_PASSWORD", ""),
    }


def can_connect_to_test_db():
    config = get_test_db_config()
    try:
        conninfo = (
            f"dbname={config['database']} "
            f"user={config['user']} "
            f"password='{config['password']}' "
            f"host={config['host']} "
            f"port={config['port']}"
        )
        pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=1, open=True)
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        pool.close()
        return True
    except Exception:
        return False


@pytest.fixture
def test_db_pool():
    if not can_connect_to_test_db():
        pytest.skip("Test database not available")
    config = get_test_db_config()
    conninfo = (
        f"dbname={config['database']} "
        f"user={config['user']} "
        f"password='{config['password']}' "
        f"host={config['host']} "
        f"port={config['port']}"
    )
    pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def clean_test_db(test_db_pool):
    with test_db_pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS glossary_terms CASCADE")
            cursor.execute("DROP TABLE IF EXISTS chapters CASCADE")
            cursor.execute("DROP TABLE IF EXISTS volumes CASCADE")
            cursor.execute("DROP TABLE IF EXISTS works CASCADE")
            cursor.execute("DROP EXTENSION IF EXISTS btree_gin CASCADE")
        conn.commit()
    yield test_db_pool


@pytest.mark.integration
class TestDatabaseInitializerIntegration:
    def test_ensure_tables_exist_creates_all_tables(self, clean_test_db):
        initializer = DatabaseInitializer()
        initializer.ensure_tables_exist(clean_test_db)
        expected_tables = {"works", "volumes", "chapters", "glossary_terms"}
        with clean_test_db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                tables = {row[0] for row in cursor.fetchall()}
        assert expected_tables.issubset(tables)

    def test_ensure_tables_exist_is_idempotent(self, clean_test_db):
        initializer = DatabaseInitializer()
        initializer.ensure_tables_exist(clean_test_db)
        with clean_test_db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                tables_after_first = {row[0] for row in cursor.fetchall()}
        initializer.ensure_tables_exist(clean_test_db)
        with clean_test_db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                tables_after_second = {row[0] for row in cursor.fetchall()}
        assert tables_after_first == tables_after_second

    def test_ensure_tables_exist_creates_btree_gin_extension(self, clean_test_db):
        initializer = DatabaseInitializer()
        initializer.ensure_tables_exist(clean_test_db)
        with clean_test_db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT extname FROM pg_extension WHERE extname = 'btree_gin'"
                )
                result = cursor.fetchone()
        assert result is not None
        assert result[0] == "btree_gin"
