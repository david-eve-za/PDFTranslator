import pytest
from pdftranslator.database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    EntityNotFoundError,
    DuplicateEntityError,
)


def test_database_error_is_base_exception():
    with pytest.raises(DatabaseError):
        raise DatabaseError("test error")


def test_connection_error_inherits_from_database_error():
    assert issubclass(ConnectionError, DatabaseError)


def test_query_error_inherits_from_database_error():
    assert issubclass(QueryError, DatabaseError)


def test_entity_not_found_error_inherits_from_database_error():
    assert issubclass(EntityNotFoundError, DatabaseError)


def test_duplicate_entity_error_inherits_from_database_error():
    assert issubclass(DuplicateEntityError, DatabaseError)


def test_exception_message():
    error = DatabaseError("test message")
    assert str(error) == "test message"
