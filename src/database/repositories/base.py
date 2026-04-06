from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Interfaz base para repositorios"""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """Obtiene una entidad por su ID"""
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """Obtiene todas las entidades"""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """Crea una nueva entidad"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Actualiza una entidad existente"""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Elimina una entidad por su ID"""
        pass
