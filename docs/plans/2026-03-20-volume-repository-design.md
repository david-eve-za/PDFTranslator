# Volume Repository Implementation Design

## Overview
Crear repositorio separado para Volume con CRUD completo y refactorizar BookRepository para eliminar métodos de Volume.

## Architecture

### New File: `database/repositories/volume_repository.py`
- `VolumeRepository(BaseRepository[Volume])` with full CRUD
- Additional methods for common queries

### Refactored Files
- `database/repositories/book_repository.py` - Remove Volume methods
- `cli/commands/split_text.py` - Use VolumeRepository
- `cli/commands/add_to_database.py` - Use VolumeRepository
- `database/repositories/__init__.py` - Export VolumeRepository

## VolumeRepository Methods

### CRUD Base Methods (from BaseRepository)
| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_id` | `(id: int) -> Optional[Volume]` | Get volume by ID |
| `get_all` | `() -> List[Volume]` | Get all volumes |
| `create` | `(entity: Volume) -> Volume` | Create new volume |
| `update` | `(entity: Volume) -> Volume` | Update existing volume |
| `delete` | `(id: int) -> bool` | Delete volume by ID |

### Additional Methods
| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_work_id` | `(work_id: int) -> List[Volume]` | Get all volumes for a work |
| `find_by_volume_number` | `(work_id: int, volume_number: int) -> Optional[Volume]` | Find specific volume |
| `update_full_text` | `(volume_id: int, text: str) -> bool` | Update only full_text field |

## BookRepository Changes

### Methods to Remove
- `get_volumes(work_id)` → `VolumeRepository.get_by_work_id()`
- `add_volume(volume)` → `VolumeRepository.create()`
- `get_volume_by_id(volume_id)` → `VolumeRepository.get_by_id()`

### Methods to Keep (Work-related only)
- `get_by_id`, `get_all`, `create`, `update`, `delete` (Work CRUD)
- `find_by_title`
- `find_similar_works`
- `find_all`

## File Changes

### 1. Create `database/repositories/volume_repository.py`

```python
from typing import Optional, List
from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import Volume

class VolumeRepository(BaseRepository[Volume]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
    
    def _row_to_volume(self, row: tuple) -> Volume:
        return Volume(
            id=row[0],
            work_id=row[1],
            volume_number=row[2],
            title=row[3],
            full_text=row[4],
            translated_text=row[5],
        )
    
    # CRUD methods: get_by_id, get_all, create, update, delete
    
    def get_by_work_id(self, work_id: int) -> List[Volume]:
        """Get all volumes for a work."""
        ...
    
    def find_by_volume_number(self, work_id: int, volume_number: int) -> Optional[Volume]:
        """Find specific volume by work and number."""
        ...
    
    def update_full_text(self, volume_id: int, text: str) -> bool:
        """Update only the full_text field."""
        ...
```

### 2. Modify `cli/commands/split_text.py`

Replace:
```python
from database.repositories.book_repository import BookRepository
# ...
repo = BookRepository()
# ...
update_volume_text(repo, selected_volume.id, content_without_header)
```

With:
```python
from database.repositories.volume_repository import VolumeRepository
# ...
volume_repo = VolumeRepository()
# ...
volume_repo.update_full_text(selected_volume.id, content_without_header)
```

### 3. Modify `cli/commands/add_to_database.py`

Replace:
```python
repo.get_volumes(work.id)
repo.add_volume(volume)
```

With:
```python
volume_repo.get_by_work_id(work.id)
volume_repo.create(volume)
```

### 4. Update `database/repositories/__init__.py`

Add:
```python
from database.repositories.volume_repository import VolumeRepository
```

## Implementation Order

1. Create `VolumeRepository` with all methods
2. Update `split_text.py` to use `VolumeRepository`
3. Update `add_to_database.py` to use `VolumeRepository`
4. Remove Volume methods from `BookRepository`
5. Update `__init__.py` exports
6. Run tests to verify

## Error Handling

- `get_by_id`: Return `None` if not found
- `update`: Return `None` if not found, else updated entity
- `delete`: Return `True` if deleted, `False` if not found
- `update_full_text`: Return `True` on success, `False` on failure
