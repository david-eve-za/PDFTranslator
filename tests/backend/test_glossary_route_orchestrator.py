"""Tests for glossary.py route using GlossaryBuildOrchestrator."""
import inspect

from pdftranslator.backend.api.routes.glossary import (
    build_glossary,
    get_glossary_build_orchestrator,
)


def test_glossary_build_uses_orchestrator():
    sig = inspect.signature(build_glossary)
    assert "orchestrator" in sig.parameters


def test_no_glossary_manager_import():
    source = inspect.getsource(inspect.getmodule(build_glossary))
    assert "GlossaryManager" not in source
    assert "GlossaryBuildOrchestrator" in source


def test_orchestrator_provider_returns_orchestrator():
    from pdftranslator.application.services.glossary_build_orchestrator import GlossaryBuildOrchestrator

    result = get_glossary_build_orchestrator
    assert callable(result)
