"""
Domain models for Glossary Service.

CUPID Principle: Domain-Focused
- Rich domain models with invariants
- No infrastructure dependencies
- Self-validating business rules
"""

from .build_pipeline import (
    BuildPipeline,
    PipelineStage,
    PipelineStageStatus,
    BuildPipelineStatus,
)
from .glossary import Glossary, GlossaryEntry, GlossaryStatus
from .entity import EntityCandidate, EntityType

__all__ = [
    # Build Pipeline
    "BuildPipeline",
    "PipelineStage",
    "PipelineStageStatus",
    "BuildPipelineStatus",
    # Glossary
    "Glossary",
    "GlossaryEntry",
    "GlossaryStatus",
    # Entity
    "EntityCandidate",
    "EntityType",
]