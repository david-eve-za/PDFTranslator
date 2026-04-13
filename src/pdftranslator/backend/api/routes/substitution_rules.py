"""Substitution rules management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from pdftranslator.backend.api.models.schemas import (
    SubstitutionRuleResponse,
    SubstitutionRuleCreate,
    SubstitutionRuleUpdate,
    ApplyRulesRequest,
)
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.substitution_rule_repository import (
    SubstitutionRuleRepository,
)
from pdftranslator.services.text_substitution_service import TextSubstitutionService

router = APIRouter(prefix="/api/substitution-rules", tags=["substitution-rules"])


def get_rule_repository() -> SubstitutionRuleRepository:
    return SubstitutionRuleRepository(DatabasePool.get_instance())


def get_substitution_service() -> TextSubstitutionService:
    return TextSubstitutionService()


@router.get("/", response_model=list[SubstitutionRuleResponse])
async def list_rules(
    active_only: bool = False,
    repo: SubstitutionRuleRepository = Depends(get_rule_repository),
):
    """List all substitution rules."""
    rules = repo.get_all(active_only=active_only)
    return [_rule_to_response(r) for r in rules]


@router.get("/{rule_id}", response_model=SubstitutionRuleResponse)
async def get_rule(
    rule_id: int,
    repo: SubstitutionRuleRepository = Depends(get_rule_repository),
):
    """Get a substitution rule by ID."""
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response(rule)


@router.post("/", response_model=SubstitutionRuleResponse, status_code=201)
async def create_rule(
    data: SubstitutionRuleCreate,
    repo: SubstitutionRuleRepository = Depends(get_rule_repository),
):
    """Create a new substitution rule."""
    from pdftranslator.database.models import SubstitutionRule

    rule = SubstitutionRule(
        name=data.name,
        pattern=data.pattern,
        replacement=data.replacement,
        description=data.description,
        is_active=data.is_active,
        apply_on_extract=data.apply_on_extract,
    )
    created = repo.create(rule)
    return _rule_to_response(created)


@router.put("/{rule_id}", response_model=SubstitutionRuleResponse)
async def update_rule(
    rule_id: int,
    data: SubstitutionRuleUpdate,
    repo: SubstitutionRuleRepository = Depends(get_rule_repository),
):
    """Update a substitution rule."""
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if data.name is not None:
        rule.name = data.name
    if data.pattern is not None:
        rule.pattern = data.pattern
    if data.replacement is not None:
        rule.replacement = data.replacement
    if data.description is not None:
        rule.description = data.description
    if data.is_active is not None:
        rule.is_active = data.is_active
    if data.apply_on_extract is not None:
        rule.apply_on_extract = data.apply_on_extract

    updated = repo.update(rule)
    return _rule_to_response(updated)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    repo: SubstitutionRuleRepository = Depends(get_rule_repository),
):
    """Delete a substitution rule."""
    deleted = repo.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted", "id": rule_id}


@router.post("/apply/{volume_id}")
async def apply_rules_to_volume(
    volume_id: int,
    data: ApplyRulesRequest = None,
    service: TextSubstitutionService = Depends(get_substitution_service),
):
    """Apply substitution rules to a volume's text."""
    rule_ids = data.rule_ids if data else None
    result = service.apply_to_volume(volume_id, rule_ids)
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to apply rules")
        )
    return result


def _rule_to_response(rule) -> dict:
    """Convert rule to response dict."""
    return {
        "id": rule.id,
        "name": rule.name,
        "pattern": rule.pattern,
        "replacement": rule.replacement,
        "description": rule.description,
        "is_active": rule.is_active,
        "apply_on_extract": rule.apply_on_extract,
        "created_at": rule.created_at.isoformat()
        if rule.created_at
        else datetime.now().isoformat(),
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }
