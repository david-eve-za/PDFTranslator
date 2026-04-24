"""Translation configuration routes."""

from typing import List

from fastapi import APIRouter

from pdftranslator.core.config.llm import BCP47Language, LLMProvider

router = APIRouter(prefix="/api", tags=["translation"])


@router.get("/languages")
async def get_languages() -> List[dict]:
    """Get supported languages for translation."""
    return [
        {"code": lang.value, "name": lang.name.replace("_", " ").title()}
        for lang in BCP47Language
    ]


@router.get("/providers")
async def get_providers() -> List[dict]:
    """Get available LLM providers."""
    return [
        {
            "id": provider.value,
            "name": provider.value.upper(),
            "description": f"{provider.value.capitalize()} LLM provider",
        }
        for provider in LLMProvider
    ]
