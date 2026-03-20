# Auto-inicialización de Base de Datos

## Problema
Los repositorios devuelven errores cuando las tablas no existen. No hay validación ni inicialización automática.

## Solución
Agregar auto-inicialización de schemas al crear el pool de conexión.

## Arquitectura

### Nuevo módulo: `database/initializer.py`
- Clase `DatabaseInitializer` con método estático `ensure_tables_exist(pool: ConnectionPool)`
- Verifica si tabla `works` existe consultando `information_schema.tables`
- Si no existe, ejecuta scripts SQL desde `database/schemas/*.sql` en orden alfabético

### Modificación: `database/connection.py`
- `get_sync_pool()` llama a `DatabaseInitializer.ensure_tables_exist()` antes de retornar el pool
- `get_async_pool()` llama a versión async del inicializador

## Flujo
1. Usuario llama `repo.get_by_id()` → crea pool si no existe
2. `get_sync_pool()` crea `ConnectionPool`
3. `DatabaseInitializer.ensure_tables_exist(pool)` verifica tabla `works`
4. Si no existe: lee y ejecuta scripts SQL en orden (001_extensions.sql, 002_works.sql, etc.)
5. Retorna pool inicializado

## Decisiones
- Verificar solo tabla `works` (tabla raíz del schema)
- Ordenar scripts por nombre de archivo (prefijo numérico)
- Usar `CREATE TABLE IF NOT EXISTS` ya existente en scripts
- Logs informativos sobre inicialización

## Archivos afectados
- **Nuevo**: `database/initializer.py`
- **Modificado**: `database/connection.py`
- **Modificado**: `database/__init__.py` (exportar `DatabaseInitializer`)
