"""
Glossary Service API Routes Package.
"""

from .health import router as health_router
from .glossary import router as glossary_router

__all__ = ["health_router", "glossary_router"]