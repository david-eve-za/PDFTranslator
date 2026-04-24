import pytest
from abc import ABC
from database.repositories.base import BaseRepository


def test_base_repository_is_abstract():
    assert issubclass(BaseRepository, ABC)


def test_base_repository_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseRepository()


def test_base_repository_has_required_methods():
    methods = ["get_by_id", "get_all", "create", "update", "delete"]
    for method in methods:
        assert hasattr(BaseRepository, method)
