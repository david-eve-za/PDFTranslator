class DatabaseError(Exception):
    """Error base de base de datos"""

    pass


class ConnectionError(DatabaseError):
    """Error de conexión a la base de datos"""

    pass


class QueryError(DatabaseError):
    """Error en consulta SQL"""

    pass


class EntityNotFoundError(DatabaseError):
    """Entidad no encontrada"""

    pass


class DuplicateEntityError(DatabaseError):
    """Entidad duplicada"""

    pass
