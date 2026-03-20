# Centralización de ConnectionPool en DatabasePool

## Problema
Cada repositorio (`BookRepository`, `ChapterRepository`, `GlossaryRepository`) crea su propio `ConnectionPool`, duplicando código y conexiones a la base de datos.

## Solución
Convertir `DatabasePool` en singleton que lee configuración de `GlobalConfig`. Los repositorios obtienen el pool centralizado.

## Arquitectura

### DatabasePool como Singleton
- Patrón singleton con método `get_instance()`
- Constructor lee de `GlobalConfig` si no se proporcionan parámetros
- Métodos existentes `get_sync_pool()` y `get_async_pool()` sin cambios

### Repositorios
- Constructor simplificado: `__init__(self, pool: Optional[DatabasePool] = None)`
- Eliminar `_conninfo`, `_min_size`, `_max_size`, `_pool` del repositorio
- Eliminar método `_get_pool()`
- Usar `self._pool.get_sync_pool()` para obtener conexiones

## Cambios en API

**Antes:**
```python
repo = BookRepository(host="localhost", port=5432, database="db", user="user", password="pass")
```

**Después:**
```python
repo = BookRepository()  # Usa GlobalConfig automáticamente
# O para testing:
repo = BookRepository(pool=custom_database_pool)
```

## Archivos afectados
- **Modificado**: `database/connection.py` - añadir patrón singleton
- **Modificado**: `database/repositories/book_repository.py`
- **Modificado**: `database/repositories/chapter_repository.py`
- **Modificado**: `database/repositories/glossary_repository.py`
- **Modificado**: `tests/database/test_connection.py`
- **Modificado**: `tests/database/test_book_repository.py`
- **Modificado**: `tests/database/test_chapter_repository.py`
- **Modificado**: `tests/database/test_glossary_repository.py`
