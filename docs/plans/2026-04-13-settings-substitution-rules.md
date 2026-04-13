# Settings UI + Text Substitution Rules Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a settings screen to manage backend configuration and add text substitution rules with regex patterns that can be applied automatically on extraction or manually.

**Architecture:** Backend provides REST endpoints for settings CRUD and substitution rules management. Frontend has a tabbed settings UI with form validation. Text substitution service applies regex rules to volume text.

**Tech Stack:** FastAPI, Angular 17+, PostgreSQL, Pydantic, existing Settings infrastructure

---

## Task 1: Create Database Schema for Substitution Rules

**Files:**
- Create: `src/pdftranslator/database/schemas/013_substitution_rules.sql`

**Step 1: Create SQL migration file**
```sql
-- database/schemas/013_substitution_rules.sql
CREATE TABLE IF NOT EXISTS text_substitution_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    pattern VARCHAR(500) NOT NULL,
    replacement VARCHAR(500) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    apply_on_extract BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_substitution_rules_active ON text_substitution_rules(is_active);
CREATE INDEX idx_substitution_rules_apply ON text_substitution_rules(apply_on_extract);
```

**Step 2: Commit**
```bash
git add src/pdftranslator/database/schemas/013_substitution_rules.sql
git commit -m "feat(database): add substitution rules table schema"
```

---

## Task 2: Create Substitution Rule Model and Repository

**Files:**
- Create: `src/pdftranslator/database/models.py` (append)
- Create: `src/pdftranslator/database/repositories/substitution_rule_repository.py`

**Step 1: Add SubstitutionRule to models**
Add to `src/pdftranslator/database/models.py`:
```python
@dataclass
class SubstitutionRule:
    """Text substitution rule with regex pattern."""
    id: Optional[int] = None
    name: str = ""
    pattern: str = ""
    replacement: str = ""
    description: Optional[str] = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Step 2: Create repository**
```python
"""Substitution rule repository."""

from typing import Optional, List
from datetime import datetime

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import SubstitutionRule


class SubstitutionRuleRepository(BaseRepository[SubstitutionRule]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_rule(self, row: tuple) -> SubstitutionRule:
        return SubstitutionRule(
            id=row[0],
            name=row[1],
            pattern=row[2],
            replacement=row[3],
            description=row[4] if len(row) > 4 else None,
            is_active=row[5] if len(row) > 5 else True,
            apply_on_extract=row[6] if len(row) > 6 else True,
            created_at=row[7] if len(row) > 7 else None,
            updated_at=row[8] if len(row) > 8 else None,
        )

    def get_by_id(self, id: int) -> Optional[SubstitutionRule]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_rule(row) if row else None

    def get_all(self, active_only: bool = False) -> List[SubstitutionRule]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                """
                if active_only:
                    query += " WHERE is_active = TRUE"
                query += " ORDER BY name"
                cur.execute(query)
                rows = cur.fetchall()
                return [self._row_to_rule(row) for row in rows]

    def get_auto_apply_rules(self) -> List[SubstitutionRule]:
        """Get rules that should be applied on extraction."""
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, pattern, replacement, description,
                           is_active, apply_on_extract, created_at, updated_at
                    FROM text_substitution_rules
                    WHERE is_active = TRUE AND apply_on_extract = TRUE
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_rule(row) for row in rows]

    def create(self, entity: SubstitutionRule) -> SubstitutionRule:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO text_substitution_rules
                        (name, pattern, replacement, description, is_active, apply_on_extract)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, pattern, replacement, description,
                              is_active, apply_on_extract, created_at, updated_at
                    """,
                    (
                        entity.name,
                        entity.pattern,
                        entity.replacement,
                        entity.description,
                        entity.is_active,
                        entity.apply_on_extract,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_rule(row)

    def update(self, entity: SubstitutionRule) -> SubstitutionRule:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE text_substitution_rules
                    SET name = %s, pattern = %s, replacement = %s,
                        description = %s, is_active = %s, apply_on_extract = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, pattern, replacement, description,
                              is_active, apply_on_extract, created_at, updated_at
                    """,
                    (
                        entity.name,
                        entity.pattern,
                        entity.replacement,
                        entity.description,
                        entity.is_active,
                        entity.apply_on_extract,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_rule(row) if row else None

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM text_substitution_rules WHERE id = %s", (id,))
                return cur.rowcount > 0
```

**Step 3: Commit**
```bash
git add src/pdftranslator/database/models.py
git add src/pdftranslator/database/repositories/substitution_rule_repository.py
git commit -m "feat(database): add SubstitutionRule model and repository"
```

---

## Task 3: Create Text Substitution Service

**Files:**
- Create: `src/pdftranslator/services/text_substitution_service.py`

**Step 1: Create service**
```python
"""Text substitution service for applying regex rules."""

import re
import logging
from typing import List

from pdftranslator.database.models import SubstitutionRule
from pdftranslator.database.repositories.substitution_rule_repository import SubstitutionRuleRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.connection import DatabasePool

logger = logging.getLogger(__name__)


class TextSubstitutionService:
    """Apply text substitution rules to content."""

    def __init__(self):
        self._rule_repo = SubstitutionRuleRepository(DatabasePool.get_instance())
        self._volume_repo = VolumeRepository(DatabasePool.get_instance())

    def apply_rules(self, text: str, rules: List[SubstitutionRule]) -> str:
        """
        Apply all active rules to text.

        Args:
            text: Text to process
            rules: List of substitution rules

        Returns:
            Text with substitutions applied
        """
        result = text
        for rule in rules:
            if rule.is_active:
                try:
                    result = re.sub(rule.pattern, rule.replacement, result)
                    logger.debug(f"Applied rule '{rule.name}': {rule.pattern} -> {rule.replacement}")
                except re.error as e:
                    logger.error(f"Invalid regex pattern in rule '{rule.name}': {e}")
        return result

    def apply_to_text(self, text: str, rule_ids: List[int] = None) -> str:
        """
        Apply specific rules or all active rules to text.

        Args:
            text: Text to process
            rule_ids: Optional list of specific rule IDs to apply

        Returns:
            Text with substitutions applied
        """
        if rule_ids:
            rules = [self._rule_repo.get_by_id(rid) for rid in rule_ids]
            rules = [r for r in rules if r is not None]
        else:
            rules = self._rule_repo.get_all(active_only=True)
        return self.apply_rules(text, rules)

    def apply_to_volume(self, volume_id: int, rule_ids: List[int] = None) -> dict:
        """
        Apply rules to a volume's full_text.

        Args:
            volume_id: Volume ID
            rule_ids: Optional list of specific rule IDs

        Returns:
            Dict with success status and stats
        """
        volume = self._volume_repo.get_by_id(volume_id)
        if not volume:
            return {"success": False, "error": "Volume not found"}

        if not volume.full_text:
            return {"success": False, "error": "Volume has no text content"}

        original_text = volume.full_text
        processed_text = self.apply_to_text(original_text, rule_ids)

        if processed_text == original_text:
            return {"success": True, "changes": 0, "message": "No changes made"}

        self._volume_repo.update_full_text(volume_id, processed_text)

        return {
            "success": True,
            "changes": 1,
            "original_length": len(original_text),
            "processed_length": len(processed_text),
        }

    def get_auto_apply_rules(self) -> List[SubstitutionRule]:
        """Get rules that should be applied automatically on extraction."""
        return self._rule_repo.get_auto_apply_rules()
```

**Step 2: Commit**
```bash
git add src/pdftranslator/services/text_substitution_service.py
git commit -m "feat(services): add TextSubstitutionService for regex rules"
```

---

## Task 4: Add API Schemas

**Files:**
- Modify: `src/pdftranslator/backend/api/models/schemas.py`

**Step 1: Add schemas at the end of file**
```python
class SubstitutionRuleResponse(BaseModel):
    """Substitution rule response schema."""
    id: int
    name: str
    pattern: str
    replacement: str
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: str
    updated_at: str | None = None


class SubstitutionRuleCreate(BaseModel):
    """Substitution rule create request schema."""
    name: str
    pattern: str
    replacement: str
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True


class SubstitutionRuleUpdate(BaseModel):
    """Substitution rule update request schema."""
    name: str | None = None
    pattern: str | None = None
    replacement: str | None = None
    description: str | None = None
    is_active: bool | None = None
    apply_on_extract: bool | None = None


class SettingsResponse(BaseModel):
    """Settings response schema (secrets masked)."""
    llm: dict
    database: dict
    document: dict
    nlp: dict
    paths: dict


class SettingsUpdateRequest(BaseModel):
    """Settings update request schema."""
    llm: dict | None = None
    database: dict | None = None
    document: dict | None = None
    nlp: dict | None = None
    paths: dict | None = None


class ApplyRulesRequest(BaseModel):
    """Request to apply rules to a volume."""
    rule_ids: list[int] | None = None
```

**Step 2: Commit**
```bash
git add src/pdftranslator/backend/api/models/schemas.py
git commit -m "feat(api): add schemas for settings and substitution rules"
```

---

## Task 5: Create Substitution Rules Routes

**Files:**
- Create: `src/pdftranslator/backend/api/routes/substitution_rules.py`

**Step 1: Create routes file**
```python
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
from pdftranslator.database.repositories.substitution_rule_repository import SubstitutionRuleRepository
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
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to apply rules"))
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
        "created_at": rule.created_at.isoformat() if rule.created_at else datetime.now().isoformat(),
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }
```

**Step 2: Commit**
```bash
git add src/pdftranslator/backend/api/routes/substitution_rules.py
git commit -m "feat(backend): add substitution rules CRUD endpoints"
```

---

## Task 6: Create Settings Routes

**Files:**
- Create: `src/pdftranslator/backend/api/routes/settings.py`

**Step 1: Create settings routes**
```python
"""Settings management routes."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pdftranslator.backend.api.models.schemas import SettingsResponse, SettingsUpdateRequest
from pdftranslator.core.config.settings import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=SettingsResponse)
async def get_settings_api():
    """Get current settings (secrets masked)."""
    settings = get_settings()
    return _settings_to_response(settings)


@router.put("/")
async def update_settings(data: SettingsUpdateRequest):
    """Update settings and write to .env file."""
    settings = get_settings()
    env_updates = {}

    if data.llm:
        env_updates.update(_flatten_llm_settings(data.llm))
    if data.database:
        env_updates.update(_flatten_db_settings(data.database))
    if data.document:
        env_updates.update(_flatten_doc_settings(data.document))
    if data.nlp:
        env_updates.update(_flatten_nlp_settings(data.nlp))
    if data.paths:
        env_updates.update(_flatten_path_settings(data.paths))

    if env_updates:
        _update_env_file(env_updates)

    return {"message": "Settings updated. Restart backend to apply changes.", "restart_required": True}


@router.post("/restart")
async def restart_backend():
    """Request backend restart ( informational - actual restart handled externally)."""
    return {"message": "Restart signal sent. Please restart the backend manually or via orchestrator."}


def _settings_to_response(settings: Settings) -> dict:
    """Convert settings to response dict, masking secrets."""
    return {
        "llm": {
            "agent": settings.llm.agent.value,
            "nvidia": {
                "model_name": settings.llm.nvidia.model_name,
                "temperature": settings.llm.nvidia.temperature,
                "top_p": settings.llm.nvidia.top_p,
                "max_output_tokens": settings.llm.nvidia.max_output_tokens,
            },
            "gemini": {
                "model_names": settings.llm.gemini.model_names,
                "temperature": settings.llm.gemini.temperature,
                "top_p": settings.llm.gemini.top_p,
            },
            "ollama": {
                "model_name": settings.llm.ollama.model_name,
                "temperature": settings.llm.ollama.temperature,
            },
            "nvidia_api_key": "***" if settings.llm.nvidia_api_key else "",
            "google_api_key": "***" if settings.llm.google_api_key else "",
        },
        "database": {
            "host": settings.database.host,
            "port": settings.database.port,
            "name": settings.database.name,
            "user": settings.database.user,
            "password": "***",
            "min_connections": settings.database.min_connections,
            "max_connections": settings.database.max_connections,
        },
        "document": {
            "enable_ocr": settings.document.enable_ocr,
            "ocr_languages": settings.document.ocr_languages,
            "accelerator_device": settings.document.accelerator_device,
            "do_table_structure": settings.document.do_table_structure,
            "generate_page_images": settings.document.generate_page_images,
        },
        "nlp": {
            "sentence_model": settings.nlp.sentence_model,
        },
        "paths": {
            "translation_prompt_path": str(settings.paths.translation_prompt_path),
            "output_dir": str(settings.paths.output_dir),
        },
    }


def _flatten_llm_settings(data: dict) -> dict:
    """Flatten LLM settings to env variable names."""
    result = {}
    if "agent" in data:
        result["LLM__AGENT"] = data["agent"]
    if "nvidia" in data:
        for key, value in data["nvidia"].items():
            result[f"LLM__NVIDIA__{key.upper()}"] = str(value)
    if "gemini" in data:
        for key, value in data["gemini"].items():
            result[f"LLM__GEMINI__{key.upper()}"] = str(value)
    if "ollama" in data:
        for key, value in data["ollama"].items():
            result[f"LLM__OLLAMA__{key.upper()}"] = str(value)
    if "nvidia_api_key" in data and data["nvidia_api_key"] != "***":
        result["NVIDIA_API_KEY"] = data["nvidia_api_key"]
    if "google_api_key" in data and data["google_api_key"] != "***":
        result["GOOGLE_API_KEY"] = data["google_api_key"]
    return result


def _flatten_db_settings(data: dict) -> dict:
    """Flatten database settings to env variable names."""
    result = {}
    mapping = {
        "host": "DB_HOST",
        "port": "DB_PORT",
        "name": "DB_NAME",
        "user": "DB_USER",
        "password": "DB_PASSWORD",
        "min_connections": "DB_MIN_CONNECTIONS",
        "max_connections": "DB_MAX_CONNECTIONS",
    }
    for key, env_key in mapping.items():
        if key in data and (key != "password" or data[key] != "***"):
            result[env_key] = str(data[key])
    return result


def _flatten_doc_settings(data: dict) -> dict:
    """Flatten document settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"DOCUMENT__{key.upper()}"] = str(value)
    return result


def _flatten_nlp_settings(data: dict) -> dict:
    """Flatten NLP settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"NLP__{key.upper()}"] = str(value)
    return result


def _flatten_path_settings(data: dict) -> dict:
    """Flatten path settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"PATHS__{key.upper()}"] = str(value)
    return result


def _update_env_file(updates: dict) -> None:
    """Update .env file with new values."""
    env_path = Path(".env")
    
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_lines = f.readlines()
    
    existing_keys = {}
    for i, line in enumerate(existing_lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            existing_keys[key] = i
    
    for key, value in updates.items():
        line = f"{key}={value}\n"
        if key in existing_keys:
            existing_lines[existing_keys[key]] = line
        else:
            existing_lines.append(line)
    
    with open(env_path, "w") as f:
        f.writelines(existing_lines)
```

**Step 2: Commit**
```bash
git add src/pdftranslator/backend/api/routes/settings.py
git commit -m "feat(backend): add settings CRUD endpoints with .env update"
```

---

## Task 7: Register Routes in Backend

**Files:**
- Modify: `src/pdftranslator/backend/api/routes/__init__.py`
- Modify: `src/pdftranslator/backend/main.py`

**Step 1: Update routes/__init__.py**
Add imports:
```python
from pdftranslator.backend.api.routes import (
    files,
    glossary,
    translation,
    works,
    volumes,
    chapters,
    split,
    settings,
    substitution_rules,
)

__all__ = ["files", "glossary", "translation", "works", "volumes", "chapters", "split", "settings", "substitution_rules"]
```

**Step 2: Update main.py**
Add routers:
```python
from pdftranslator.backend.api.routes import (
    files,
    glossary,
    translation,
    works,
    volumes,
    chapters,
    split,
    settings,
    substitution_rules,
)

app.include_router(settings.router)
app.include_router(substitution_rules.router)
```

**Step 3: Commit**
```bash
git add src/pdftranslator/backend/api/routes/__init__.py
git add src/pdftranslator/backend/main.py
git commit -m "feat(backend): register settings and substitution_rules routers"
```

---

## Task 8: Create Frontend Services

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/services/settings.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/substitution-rule.service.ts`

**Step 1: Create settings.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SettingsResponse {
  llm: {
    agent: string;
    nvidia: {
      model_name: string;
      temperature: number;
      top_p: number;
      max_output_tokens: number;
    };
    gemini: {
      model_names: string[];
      temperature: number;
      top_p: number;
    };
    ollama: {
      model_name: string;
      temperature: number;
    };
    nvidia_api_key: string;
    google_api_key: string;
  };
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
    min_connections: number;
    max_connections: number;
  };
  document: {
    enable_ocr: boolean;
    ocr_languages: string[];
    accelerator_device: string;
    do_table_structure: boolean;
    generate_page_images: boolean;
  };
  nlp: {
    sentence_model: string;
  };
  paths: {
    translation_prompt_path: string;
    output_dir: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private apiUrl = '/api/settings';

  constructor(private http: HttpClient) {}

  get(): Observable<SettingsResponse> {
    return this.http.get<SettingsResponse>(this.apiUrl);
  }

  update(settings: Partial<SettingsResponse>): Observable<{ message: string; restart_required: boolean }> {
    return this.http.put<{ message: string; restart_required: boolean }>(this.apiUrl, settings);
  }

  restart(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/restart`, {});
  }
}
```

**Step 2: Create substitution-rule.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SubstitutionRule {
  id: number;
  name: string;
  pattern: string;
  replacement: string;
  description: string | null;
  is_active: boolean;
  apply_on_extract: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface SubstitutionRuleCreate {
  name: string;
  pattern: string;
  replacement: string;
  description?: string;
  is_active?: boolean;
  apply_on_extract?: boolean;
}

export interface SubstitutionRuleUpdate {
  name?: string;
  pattern?: string;
  replacement?: string;
  description?: string;
  is_active?: boolean;
  apply_on_extract?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class SubstitutionRuleService {
  private apiUrl = '/api/substitution-rules';

  constructor(private http: HttpClient) {}

  getAll(activeOnly: boolean = false): Observable<SubstitutionRule[]> {
    return this.http.get<SubstitutionRule[]>(this.apiUrl, {
      params: { active_only: activeOnly.toString() }
    });
  }

  getById(id: number): Observable<SubstitutionRule> {
    return this.http.get<SubstitutionRule>(`${this.apiUrl}/${id}`);
  }

  create(rule: SubstitutionRuleCreate): Observable<SubstitutionRule> {
    return this.http.post<SubstitutionRule>(this.apiUrl, rule);
  }

  update(id: number, rule: SubstitutionRuleUpdate): Observable<SubstitutionRule> {
    return this.http.put<SubstitutionRule>(`${this.apiUrl}/${id}`, rule);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  applyToVolume(volumeId: number, ruleIds?: number[]): Observable<{ success: boolean; changes: number }> {
    return this.http.post<{ success: boolean; changes: number }>(
      `${this.apiUrl}/apply/${volumeId}`,
      { rule_ids: ruleIds }
    );
  }
}
```

**Step 3: Commit**
```bash
git add src/pdftranslator/frontend/src/app/core/services/settings.service.ts
git add src/pdftranslator/frontend/src/app/core/services/substitution-rule.service.ts
git commit -m "feat(frontend): add settings and substitution-rule services"
```

---

## Task 9: Create Settings Component

**Files:**
- Create: `src/pdftranslator/frontend/src/app/features/settings/settings.component.ts`
- Create: `src/pdftranslator/frontend/src/app/features/settings/settings.component.html`
- Create: `src/pdftranslator/frontend/src/app/features/settings/settings.component.scss`

**Step 1: Create settings.component.ts**
```typescript
import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService, SettingsResponse } from '../../core/services/settings.service';
import { SubstitutionRuleService, SubstitutionRule, SubstitutionRuleCreate } from '../../core/services/substitution-rule.service';

type ActiveTab = 'llm' | 'database' | 'document' | 'rules';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  private settingsService = inject(SettingsService);
  private ruleService = inject(SubstitutionRuleService);

  activeTab = signal<ActiveTab>('llm');
  settings = signal<SettingsResponse | null>(null);
  rules = signal<SubstitutionRule[]>([]);
  
  isLoading = signal(false);
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);
  
  showRuleModal = signal(false);
  editingRule = signal<SubstitutionRule | null>(null);
  newRule = signal<SubstitutionRuleCreate>({
    name: '',
    pattern: '',
    replacement: '',
    is_active: true,
    apply_on_extract: true
  });

  providers = ['nvidia', 'gemini', 'ollama'];
  acceleratorDevices = ['auto', 'cpu', 'cuda', 'mps'];

  ngOnInit(): void {
    this.loadSettings();
    this.loadRules();
  }

  private loadSettings(): void {
    this.isLoading.set(true);
    this.settingsService.get().subscribe({
      next: (settings) => {
        this.settings.set(settings);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to load settings');
        this.isLoading.set(false);
        console.error('Failed to load settings:', err);
      }
    });
  }

  private loadRules(): void {
    this.ruleService.getAll().subscribe({
      next: (rules) => {
        this.rules.set(rules);
      },
      error: (err) => {
        console.error('Failed to load rules:', err);
      }
    });
  }

  setTab(tab: ActiveTab): void {
    this.activeTab.set(tab);
  }

  saveSettings(): void {
    const settings = this.settings();
    if (!settings) return;

    this.isSaving.set(true);
    this.errorMessage.set(null);

    this.settingsService.update(settings).subscribe({
      next: (response) => {
        this.successMessage.set(response.message);
        this.isSaving.set(false);
        setTimeout(() => this.successMessage.set(null), 5000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to save settings');
        this.isSaving.set(false);
        console.error('Failed to save settings:', err);
      }
    });
  }

  openRuleModal(rule?: SubstitutionRule): void {
    if (rule) {
      this.editingRule.set(rule);
    } else {
      this.editingRule.set(null);
      this.newRule.set({
        name: '',
        pattern: '',
        replacement: '',
        is_active: true,
        apply_on_extract: true
      });
    }
    this.showRuleModal.set(true);
  }

  closeRuleModal(): void {
    this.showRuleModal.set(false);
    this.editingRule.set(null);
  }

  saveRule(): void {
    const editing = this.editingRule();
    if (editing) {
      this.ruleService.update(editing.id, {
        name: editing.name,
        pattern: editing.pattern,
        replacement: editing.replacement,
        description: editing.description,
        is_active: editing.is_active,
        apply_on_extract: editing.apply_on_extract
      }).subscribe({
        next: () => {
          this.loadRules();
          this.closeRuleModal();
        },
        error: (err) => {
          this.errorMessage.set('Failed to update rule');
          console.error('Failed to update rule:', err);
        }
      });
    } else {
      this.ruleService.create(this.newRule()).subscribe({
        next: () => {
          this.loadRules();
          this.closeRuleModal();
        },
        error: (err) => {
          this.errorMessage.set('Failed to create rule');
          console.error('Failed to create rule:', err);
        }
      });
    }
  }

  deleteRule(id: number): void {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    
    this.ruleService.delete(id).subscribe({
      next: () => {
        this.rules.update(rules => rules.filter(r => r.id !== id));
      },
      error: (err) => {
        this.errorMessage.set('Failed to delete rule');
        console.error('Failed to delete rule:', err);
      }
    });
  }

  toggleRuleActive(rule: SubstitutionRule): void {
    this.ruleService.update(rule.id, { is_active: !rule.is_active }).subscribe({
      next: (updated) => {
        this.rules.update(rules =>
          rules.map(r => r.id === updated.id ? updated : r)
        );
      },
      error: (err) => {
        this.errorMessage.set('Failed to update rule');
        console.error('Failed to update rule:', err);
      }
    });
  }
}
```

**Step 2: Create settings.component.html**
```html
<div class="settings-container">
  <header class="page-header">
    <h1 class="page-title">Settings</h1>
    <p class="page-description">Configure backend and text substitution rules</p>
  </header>

  <main class="settings-content">
    <div class="tabs">
      <button
        class="tab-btn"
        [class.active]="activeTab() === 'llm'"
        (click)="setTab('llm')">
        LLM
      </button>
      <button
        class="tab-btn"
        [class.active]="activeTab() === 'database'"
        (click)="setTab('database')">
        Database
      </button>
      <button
        class="tab-btn"
        [class.active]="activeTab() === 'document'"
        (click)="setTab('document')">
        Document
      </button>
      <button
        class="tab-btn"
        [class.active]="activeTab() === 'rules'"
        (click)="setTab('rules')">
        Substitution Rules
      </button>
    </div>

    @if (isLoading()) {
      <div class="loading-state">Loading settings...</div>
    }

    @if (!isLoading() && settings()) {
      @if (activeTab() === 'llm') {
        <section class="settings-section">
          <h2>LLM Configuration</h2>
          
          <div class="form-group">
            <label class="form-label">Provider</label>
            <select class="form-select" [(ngModel)]="settings()!.llm.agent">
              @for (provider of providers; track provider) {
                <option [value]="provider">{{ provider | titlecase }}</option>
              }
            </select>
          </div>

          <h3>NVIDIA Settings</h3>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Model</label>
              <input type="text" class="form-input" [(ngModel)]="settings()!.llm.nvidia.model_name" />
            </div>
            <div class="form-group">
              <label class="form-label">Temperature</label>
              <input type="number" step="0.1" min="0" max="2" class="form-input" [(ngModel)]="settings()!.llm.nvidia.temperature" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">API Key</label>
            <input type="password" class="form-input" [(ngModel)]="settings()!.llm.nvidia_api_key" placeholder="Leave *** to keep existing" />
          </div>

          <h3>Gemini Settings</h3>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Temperature</label>
              <input type="number" step="0.1" min="0" max="2" class="form-input" [(ngModel)]="settings()!.llm.gemini.temperature" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">API Key</label>
            <input type="password" class="form-input" [(ngModel)]="settings()!.llm.google_api_key" placeholder="Leave *** to keep existing" />
          </div>

          <h3>Ollama Settings</h3>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Model</label>
              <input type="text" class="form-input" [(ngModel)]="settings()!.llm.ollama.model_name" />
            </div>
            <div class="form-group">
              <label class="form-label">Temperature</label>
              <input type="number" step="0.1" min="0" max="2" class="form-input" [(ngModel)]="settings()!.llm.ollama.temperature" />
            </div>
          </div>
        </section>
      }

      @if (activeTab() === 'database') {
        <section class="settings-section">
          <h2>Database Configuration</h2>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Host</label>
              <input type="text" class="form-input" [(ngModel)]="settings()!.database.host" />
            </div>
            <div class="form-group">
              <label class="form-label">Port</label>
              <input type="number" class="form-input" [(ngModel)]="settings()!.database.port" />
            </div>
          </div>
          
          <div class="form-group">
            <label class="form-label">Database Name</label>
            <input type="text" class="form-input" [(ngModel)]="settings()!.database.name" />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Username</label>
              <input type="text" class="form-input" [(ngModel)]="settings()!.database.user" />
            </div>
            <div class="form-group">
              <label class="form-label">Password</label>
              <input type="password" class="form-input" [(ngModel)]="settings()!.database.password" placeholder="Leave *** to keep existing" />
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Min Connections</label>
              <input type="number" class="form-input" [(ngModel)]="settings()!.database.min_connections" />
            </div>
            <div class="form-group">
              <label class="form-label">Max Connections</label>
              <input type="number" class="form-input" [(ngModel)]="settings()!.database.max_connections" />
            </div>
          </div>
        </section>
      }

      @if (activeTab() === 'document') {
        <section class="settings-section">
          <h2>Document Processing</h2>
          
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" [(ngModel)]="settings()!.document.enable_ocr" />
              <span>Enable OCR</span>
            </label>
          </div>
          
          <div class="form-group">
            <label class="form-label">Accelerator Device</label>
            <select class="form-select" [(ngModel)]="settings()!.document.accelerator_device">
              @for (device of acceleratorDevices; track device) {
                <option [value]="device">{{ device | titlecase }}</option>
              }
            </select>
          </div>
          
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" [(ngModel)]="settings()!.document.do_table_structure" />
              <span>Extract Table Structure</span>
            </label>
          </div>
          
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" [(ngModel)]="settings()!.document.generate_page_images" />
              <span>Generate Page Images</span>
            </label>
          </div>
        </section>
      }

      @if (activeTab() === 'rules') {
        <section class="settings-section">
          <div class="section-header">
            <h2>Text Substitution Rules</h2>
            <button class="btn btn-primary" (click)="openRuleModal()">
              Add Rule
            </button>
          </div>
          
          <p class="section-description">
            Define regex patterns to automatically substitute text during extraction or manually.
          </p>

          @if (rules().length === 0) {
            <div class="empty-state">
              <p>No substitution rules defined</p>
            </div>
          } @else {
            <div class="rules-list">
              @for (rule of rules(); track rule.id) {
                <div class="rule-item">
                  <div class="rule-header">
                    <h4>{{ rule.name }}</h4>
                    <div class="rule-actions">
                      <label class="toggle-label">
                        <input type="checkbox" [checked]="rule.is_active" (change)="toggleRuleActive(rule)" />
                        <span>Active</span>
                      </label>
                      <button class="btn btn-ghost" (click)="openRuleModal(rule)">Edit</button>
                      <button class="btn btn-ghost delete" (click)="deleteRule(rule.id)">Delete</button>
                    </div>
                  </div>
                  <div class="rule-details">
                    <div class="rule-field">
                      <span class="field-label">Pattern:</span>
                      <code>{{ rule.pattern }}</code>
                    </div>
                    <div class="rule-field">
                      <span class="field-label">Replacement:</span>
                      <code>{{ rule.replacement }}</code>
                    </div>
                    @if (rule.description) {
                      <div class="rule-field">
                        <span class="field-label">Description:</span>
                        <span>{{ rule.description }}</span>
                      </div>
                    }
                    <div class="rule-flags">
                      @if (rule.apply_on_extract) {
                        <span class="flag-badge">Auto-apply</span>
                      }
                    </div>
                  </div>
                </div>
              }
            </div>
          }
        </section>
      }

      @if (activeTab() !== 'rules') {
        <div class="save-actions">
          <button class="btn btn-primary" (click)="saveSettings()" [disabled]="isSaving()">
            @if (isSaving()) {
              Saving...
            } @else {
              Save Settings
            }
          </button>
          <p class="save-note">Changes require backend restart to take effect</p>
        </div>
      }
    }

    @if (errorMessage()) {
      <div class="error-message">{{ errorMessage() }}</div>
    }

    @if (successMessage()) {
      <div class="success-message">{{ successMessage() }}</div>
    }
  </main>

  @if (showRuleModal()) {
    <div class="modal-overlay" (click)="closeRuleModal()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>{{ editingRule() ? 'Edit Rule' : 'Add Substitution Rule' }}</h3>
          <button class="modal-close" (click)="closeRuleModal()">x</button>
        </div>
        <div class="modal-body">
          @if (editingRule()) {
            <div class="form-group">
              <label class="form-label">Name</label>
              <input type="text" class="form-input" [(ngModel)]="editingRule()!.name" />
            </div>
            <div class="form-group">
              <label class="form-label">Pattern (Regex)</label>
              <input type="text" class="form-input" [(ngModel)]="editingRule()!.pattern" />
            </div>
            <div class="form-group">
              <label class="form-label">Replacement</label>
              <input type="text" class="form-input" [(ngModel)]="editingRule()!.replacement" />
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <input type="text" class="form-input" [(ngModel)]="editingRule()!.description" />
            </div>
            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="editingRule()!.is_active" />
                <span>Active</span>
              </label>
            </div>
            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="editingRule()!.apply_on_extract" />
                <span>Apply on Extraction</span>
              </label>
            </div>
          } @else {
            <div class="form-group">
              <label class="form-label">Name</label>
              <input type="text" class="form-input" [(ngModel)]="newRule().name" />
            </div>
            <div class="form-group">
              <label class="form-label">Pattern (Regex)</label>
              <input type="text" class="form-input" [(ngModel)]="newRule().pattern" />
            </div>
            <div class="form-group">
              <label class="form-label">Replacement</label>
              <input type="text" class="form-input" [(ngModel)]="newRule().replacement" />
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <input type="text" class="form-input" [(ngModel)]="newRule().description" />
            </div>
            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="newRule().is_active" />
                <span>Active</span>
              </label>
            </div>
            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="newRule().apply_on_extract" />
                <span>Apply on Extraction</span>
              </label>
            </div>
          }
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" (click)="closeRuleModal()">Cancel</button>
          <button class="btn btn-primary" (click)="saveRule()">Save Rule</button>
        </div>
      </div>
    </div>
  }
</div>
```

**Step 3: Create settings.component.scss**
```scss
.settings-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;

  .page-title {
    font-size: 1.75rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .page-description {
    color: var(--text-secondary, #6b7280);
  }
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding-bottom: 0.5rem;
}

.tab-btn {
  padding: 0.5rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-secondary, #6b7280);
  border-bottom: 2px solid transparent;
  margin-bottom: -0.5rem;

  &:hover {
    color: var(--text-primary, #111827);
  }

  &.active {
    color: var(--primary, #3b82f6);
    border-bottom-color: var(--primary, #3b82f6);
  }
}

.settings-section {
  background: var(--bg-secondary, #f9fafb);
  border-radius: 0.75rem;
  padding: 1.5rem;
  margin-bottom: 1rem;

  h2 {
    margin: 0 0 1rem;
    font-size: 1.125rem;
  }

  h3 {
    margin: 1.5rem 0 0.75rem;
    font-size: 0.9375rem;
    color: var(--text-secondary, #6b7280);
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;

  h2 {
    margin: 0;
  }
}

.section-description {
  color: var(--text-secondary, #6b7280);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  margin-bottom: 1rem;

  &.checkbox-group {
    margin-bottom: 0.5rem;
  }
}

.form-label {
  display: block;
  margin-bottom: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.form-input,
.form-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: var(--bg-primary, #fff);

  &:focus {
    outline: none;
    border-color: var(--primary, #3b82f6);
  }
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
}

.save-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.save-note {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9ca3af);
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rule-item {
  background: var(--bg-primary, #fff);
  border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e5e7eb);
  padding: 1rem;
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;

  h4 {
    margin: 0;
    font-size: 0.9375rem;
  }
}

.rule-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.rule-details {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.rule-field {
  display: flex;
  gap: 0.5rem;
  font-size: 0.8125rem;

  .field-label {
    color: var(--text-secondary, #6b7280);
    min-width: 80px;
  }

  code {
    background: var(--bg-tertiary, #f3f4f6);
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-family: monospace;
    font-size: 0.75rem;
  }
}

.rule-flags {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.flag-badge {
  font-size: 0.6875rem;
  padding: 0.125rem 0.375rem;
  background: var(--primary, #3b82f6);
  color: white;
  border-radius: 0.25rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary, #6b7280);
}

.error-message,
.success-message {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  margin-top: 1rem;
  font-size: 0.875rem;
}

.error-message {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.success-message {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0.5rem;
  cursor: pointer;
  border: none;
  transition: all 0.15s;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: var(--primary, #3b82f6);
  color: white;

  &:hover:not(:disabled) {
    background: var(--primary-dark, #2563eb);
  }
}

.btn-secondary {
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #111827);
  border: 1px solid var(--border-color, #e5e7eb);

  &:hover:not(:disabled) {
    background: var(--bg-tertiary, #f3f4f6);
  }
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary, #6b7280);
  padding: 0.375rem 0.5rem;

  &:hover:not(:disabled) {
    color: var(--text-primary, #111827);
  }

  &.delete:hover:not(:disabled) {
    color: #dc2626;
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary, #fff);
  border-radius: 0.75rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);

  h3 {
    margin: 0;
    font-size: 1rem;
  }

  .modal-close {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    color: var(--text-secondary, #6b7280);
    line-height: 1;

    &:hover {
      color: var(--text-primary, #111827);
    }
  }
}

.modal-body {
  padding: 1.25rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

.loading-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary, #6b7280);
}
```

**Step 4: Commit**
```bash
git add src/pdftranslator/frontend/src/app/features/settings/
git commit -m "feat(frontend): add settings component with tabs for LLM, Database, Document, and Rules"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Update CHANGELOG.md**
Add section for new features.

**Step 2: Update README.md**
Add Settings section description.

**Step 3: Commit**
```bash
git add README.md CHANGELOG.md
git commit -m "docs: update documentation for settings and substitution rules"
```

---

## Task 11: Final Commit

**Step 1: Create final commit**
```bash
git add -A
git commit -m "feat: implement settings UI and text substitution rules

- Add database schema for text_substitution_rules table
- Create SubstitutionRule model and repository
- Add TextSubstitutionService for regex rule application
- Add backend endpoints for settings CRUD and substitution rules
- Create frontend SettingsComponent with tabs
- Support auto-apply on extraction and manual apply"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-04-13-settings-substitution-rules.md`.**

Two execution options:

**1. Subagent-Driven (this session)**
- I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)**
- Open new session with executing-plans, batch execution with checkpoints

Which approach?
