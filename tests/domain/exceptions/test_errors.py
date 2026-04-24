"""Tests for domain exceptions."""
from pdftranslator.domain.exceptions.errors import (
    DBConnectionError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    QueryError,
)


def test_domain_error_is_base():
    assert issubclass(DBConnectionError, DomainError)
    assert issubclass(QueryError, DomainError)
    assert issubclass(EntityNotFoundError, DomainError)
    assert issubclass(DuplicateEntityError, DomainError)


def test_db_connection_error_does_not_shadow_builtin():
    import builtins
    assert "DBConnectionError" not in dir(builtins)
    assert "ConnectionError" in dir(builtins)


def test_backward_compat_database_imports():
    from pdftranslator.database.exceptions import (
        ConnectionError,
        DatabaseError,
    )
    assert issubclass(ConnectionError, DatabaseError)


def test_backward_compat_core_imports():
    from pdftranslator.core.exceptions import (
        ConnectionError,
        DatabaseError,
    )
    assert issubclass(ConnectionError, DatabaseError)
