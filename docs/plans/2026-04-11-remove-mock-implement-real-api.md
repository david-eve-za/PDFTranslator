# Remove Mock and Implement Real API Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove InMemoryWebApi mock completely and connect frontend to real PostgreSQL-backed FastAPI backend.

**Architecture:** Frontend Angular services call FastAPI routes which use repository pattern to interact with PostgreSQL + pgvector. Docker Compose manages database lifecycle. No mock data - everything persisted.

**Tech Stack:** Angular 17+, FastAPI, PostgreSQL 16 + pgvector, psycopg_pool, Docker Compose

---

## Phase 1: Database Infrastructure

### Task 1: Configure Environment Variables

**Files:**
- Modify: `.env`

**Step 1: Update .env with Docker credentials**
```bash
# Database (matches Docker/docker-compose.yml)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=book_translator
DB_USER=translator_user
DB_PASSWORD=uQ201/-R]f3\"j@]N7/L:

# LLM API Keys (existing)
NVIDIA_API_KEY=nvapi-xxx
GOOGLE_API_KEY=xxx
```

**Step 2: Verify .gitignore includes .env**
Run: `grep -q ".env" .gitignore && echo "OK" || echo ".env not in .gitignore"`
Expected: "OK"

**Step 3: Commit**
```bash
git add .env .gitignore
git commit -m "chore: add database credentials for Docker PostgreSQL"
```

### Task 2: Start PostgreSQL with Docker Compose

**Files:**
- None (Docker operation)

**Step 1: Navigate to Docker directory and start services**
Run: `cd Docker && docker compose up -d`
Expected: Containers "postgres_db" and "cloudbeaver_web" running

**Step 2: Verify PostgreSQL is healthy**
Run: `docker compose -f Docker/docker-compose.yml ps`
Expected: "postgres_db" status "healthy"

**Step 3: Verify database connection from host**
Run: `PGPASSWORD='uQ201/-R]f3"j@]N7/L:' psql -h localhost -U translator_user -d book_translator -c "SELECT 1"`
Expected: Output shows "1"

---

## Phase 2: Backend - Works API

### Task 3: Create Works Routes

**Files:**
- Create: `src/pdftranslator/backend/api/routes/works.py`
- Modify: `src/pdftranslator/backend/api/routes/__init__.py`
- Test: `tests/backend/api/test_works.py`

**Step 1: Write the failing test**
```python
# tests/backend/api/test_works.py
import pytest
from fastapi.testclient import TestClient
from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_works_empty():
    response = client.get("/api/works")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/backend/api/test_works.py::test_list_works_empty -v`
Expected: FAIL with 404 or route not found

**Step 3: Create works routes file**
```python
# src/pdftranslator/backend/api/routes/works.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import WorkResponse, WorkListResponse, WorkCreate, WorkUpdate
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.connection import DatabasePool

router = APIRouter(prefix="/api/works", tags=["works"])


def get_work_repository() -> BookRepository:
    pool = DatabasePool.get_instance().get_pool()
    return BookRepository(pool)


@router.get("/", response_model=WorkListResponse)
async def list_works(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    repo: BookRepository = Depends(get_work_repository),
):
    works = repo.get_all(limit=page_size, offset=(page - 1) * page_size)
    total = repo.count_all()
    items = [_work_to_response(w) for w in works]
    return WorkListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{work_id}", response_model=WorkResponse)
async def get_work(
    work_id: int,
    repo: BookRepository = Depends(get_work_repository),
):
    work = repo.get_by_id(work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return _work_to_response(work, include_volumes=True)


@router.post("/", response_model=WorkResponse, status_code=201)
async def create_work(
    work_data: WorkCreate,
    repo: BookRepository = Depends(get_work_repository),
):
    work = repo.create(work_data.model_dump())
    return _work_to_response(work)


@router.put("/{work_id}", response_model=WorkResponse)
async def update_work(
    work_id: int,
    work_data: WorkUpdate,
    repo: BookRepository = Depends(get_work_repository),
):
    work = repo.update(work_id, work_data.model_dump(exclude_unset=True))
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return _work_to_response(work)


@router.delete("/{work_id}")
async def delete_work(
    work_id: int,
    repo: BookRepository = Depends(get_work_repository),
):
    deleted = repo.delete(work_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Work not found")
    return {"message": "Work deleted", "id": work_id}


def _work_to_response(work, include_volumes: bool = False) -> dict:
    from pdftranslator.database.repositories.volume_repository import VolumeRepository
    pool = DatabasePool.get_instance().get_pool()
    volume_repo = VolumeRepository(pool)
    
    volumes = []
    if include_volumes:
        volumes = [{"id": v.id, "volume_number": v.volume_number} for v in volume_repo.get_by_work_id(work.id)]
    
    return {
        "id": work.id,
        "title": work.title,
        "title_translated": work.title_translated,
        "author": work.author,
        "source_lang": work.source_lang,
        "target_lang": work.target_lang,
        "volumes": volumes,
        "created_at": work.created_at,
        "updated_at": work.updated_at,
    }
```

**Step 4: Add schemas to models**
```python
# src/pdftranslator/backend/api/models/schemas.py
# Add after existing schemas:

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class WorkResponse(BaseModel):
    id: int
    title: str
    title_translated: Optional[str] = None
    author: str
    source_lang: str = "en"
    target_lang: str = "es"
    volumes: list[dict] = []
    created_at: datetime
    updated_at: datetime


class WorkListResponse(BaseModel):
    items: list[WorkResponse]
    total: int
    page: int
    page_size: int


class WorkCreate(BaseModel):
    title: str
    author: str
    title_translated: Optional[str] = None
    source_lang: str = "en"
    target_lang: str = "es"


class WorkUpdate(BaseModel):
    title: Optional[str] = None
    title_translated: Optional[str] = None
    author: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
```

**Step 5: Register routes in main.py**
```python
# src/pdftranslator/backend/main.py
# Add import:
from pdftranslator.backend.api.routes import works

# Add router:
app.include_router(works.router)
```

**Step 6: Run test to verify it passes**
Run: `pytest tests/backend/api/test_works.py::test_list_works_empty -v`
Expected: PASS

**Step 7: Commit**
```bash
git add src/pdftranslator/backend/api/routes/works.py src/pdftranslator/backend/api/models/schemas.py src/pdftranslator/backend/main.py tests/backend/api/test_works.py
git commit -m "feat: implement Works API with CRUD operations"
```

---

## Phase 3: Backend - Volumes API

### Task 4: Create Volumes Routes

**Files:**
- Create: `src/pdftranslator/backend/api/routes/volumes.py`
- Test: `tests/backend/api/test_volumes.py`

**Step 1: Write the failing test**
```python
# tests/backend/api/test_volumes.py
import pytest
from fastapi.testclient import TestClient
from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_volumes_by_work():
    response = client.get("/api/volumes?work_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/backend/api/test_volumes.py::test_list_volumes_by_work -v`
Expected: FAIL with 404

**Step 3: Create volumes routes file**
```python
# src/pdftranslator/backend/api/routes/volumes.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import VolumeResponse, VolumeListResponse, VolumeCreate
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.connection import DatabasePool

router = APIRouter(prefix="/api/volumes", tags=["volumes"])


def get_volume_repository() -> VolumeRepository:
    pool = DatabasePool.get_instance().get_pool()
    return VolumeRepository(pool)


@router.get("/", response_model=VolumeListResponse)
async def list_volumes(
    work_id: int = Query(..., description="Filter by work ID"),
    repo: VolumeRepository = Depends(get_volume_repository),
):
    volumes = repo.get_by_work_id(work_id)
    items = [_volume_to_response(v) for v in volumes]
    return VolumeListResponse(items=items, total=len(items))


@router.get("/{volume_id}", response_model=VolumeResponse)
async def get_volume(
    volume_id: int,
    repo: VolumeRepository = Depends(get_volume_repository),
):
    volume = repo.get_by_id(volume_id)
    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")
    return _volume_to_response(volume, include_chapters=True)


@router.post("/", response_model=VolumeResponse, status_code=201)
async def create_volume(
    volume_data: VolumeCreate,
    repo: VolumeRepository = Depends(get_volume_repository),
):
    volume = repo.create(volume_data.model_dump())
    return _volume_to_response(volume)


@router.delete("/{volume_id}")
async def delete_volume(
    volume_id: int,
    repo: VolumeRepository = Depends(get_volume_repository),
):
    deleted = repo.delete(volume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Volume not found")
    return {"message": "Volume deleted", "id": volume_id}


def _volume_to_response(volume, include_chapters: bool = False) -> dict:
    from pdftranslator.database.repositories.chapter_repository import ChapterRepository
    pool = DatabasePool.get_instance().get_pool()
    chapter_repo = ChapterRepository(pool)
    
    chapters = []
    if include_chapters:
        chapters = [{"id": c.id, "chapter_number": c.chapter_number, "title": c.title} for c in chapter_repo.get_by_volume(volume.id)]
    
    return {
        "id": volume.id,
        "work_id": volume.work_id,
        "volume_number": volume.volume_number,
        "title": volume.title,
        "chapters": chapters,
        "created_at": volume.created_at,
    }
```

**Step 4: Add volume schemas**
```python
# src/pdftranslator/backend/api/models/schemas.py
# Add after WorkUpdate:

class VolumeResponse(BaseModel):
    id: int
    work_id: int
    volume_number: int
    title: Optional[str] = None
    chapters: list[dict] = []
    created_at: datetime


class VolumeListResponse(BaseModel):
    items: list[VolumeResponse]
    total: int


class VolumeCreate(BaseModel):
    work_id: int
    volume_number: int
    title: Optional[str] = None
```

**Step 5: Register routes in main.py**
```python
# src/pdftranslator/backend/main.py
from pdftranslator.backend.api.routes import volumes
app.include_router(volumes.router)
```

**Step 6: Run test to verify it passes**
Run: `pytest tests/backend/api/test_volumes.py -v`
Expected: PASS

**Step 7: Commit**
```bash
git add src/pdftranslator/backend/api/routes/volumes.py src/pdftranslator/backend/api/models/schemas.py src/pdftranslator/backend/main.py tests/backend/api/test_volumes.py
git commit -m "feat: implement Volumes API with CRUD operations"
```

---

## Phase 4: Backend - Chapters API

### Task 5: Create Chapters Routes

**Files:**
- Create: `src/pdftranslator/backend/api/routes/chapters.py`
- Test: `tests/backend/api/test_chapters.py`

**Step 1: Write the failing test**
```python
# tests/backend/api/test_chapters.py
from fastapi.testclient import TestClient
from pdftranslator.backend.main import app

client = TestClient(app)


def test_get_chapter():
    response = client.get("/api/chapters/1")
    assert response.status_code in [200, 404]
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/backend/api/test_chapters.py -v`
Expected: FAIL with 404

**Step 3: Create chapters routes**
```python
# src/pdftranslator/backend/api/routes/chapters.py
from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import ChapterResponse, ChapterListResponse, ChapterUpdate
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.connection import DatabasePool

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def get_chapter_repository() -> ChapterRepository:
    pool = DatabasePool.get_instance().get_pool()
    return ChapterRepository(pool)


@router.get("/", response_model=ChapterListResponse)
async def list_chapters(
    volume_id: int = Query(..., description="Filter by volume ID"),
    repo: ChapterRepository = Depends(get_chapter_repository),
):
    chapters = repo.get_by_volume(volume_id)
    items = [_chapter_to_response(c) for c in chapters]
    return ChapterListResponse(items=items, total=len(items))


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: int,
    repo: ChapterRepository = Depends(get_chapter_repository),
):
    chapter = repo.get_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_to_response(chapter)


@router.put("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    chapter_data: ChapterUpdate,
    repo: ChapterRepository = Depends(get_chapter_repository),
):
    chapter = repo.update(chapter_id, chapter_data.model_dump(exclude_unset=True))
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_to_response(chapter)


def _chapter_to_response(chapter) -> dict:
    return {
        "id": chapter.id,
        "volume_id": chapter.volume_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "original_text": chapter.original_text,
        "translated_text": chapter.translated_text,
        "is_translated": chapter.is_translated,
        "created_at": chapter.created_at,
        "updated_at": chapter.updated_at,
    }
```

**Step 4: Add chapter schemas**
```python
# src/pdftranslator/backend/api/models/schemas.py
class ChapterResponse(BaseModel):
    id: int
    volume_id: int
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    is_translated: bool = False
    created_at: datetime
    updated_at: datetime


class ChapterListResponse(BaseModel):
    items: list[ChapterResponse]
    total: int


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    translated_text: Optional[str] = None
```

**Step 5: Register routes**
```python
# src/pdftranslator/backend/main.py
from pdftranslator.backend.api.routes import chapters
app.include_router(chapters.router)
```

**Step 6: Run tests**
Run: `pytest tests/backend/api/test_chapters.py -v`
Expected: PASS

**Step 7: Commit**
```bash
git add src/pdftranslator/backend/api/routes/chapters.py src/pdftranslator/backend/api/models/schemas.py src/pdftranslator/backend/main.py tests/backend/api/test_chapters.py
git commit -m "feat: implement Chapters API with read/update operations"
```

---

## Phase 5: Backend - Refactor Glossary

### Task 6: Connect Glossary Routes to Database

**Files:**
- Modify: `src/pdftranslator/backend/api/routes/glossary.py`
- Test: `tests/backend/api/test_glossary.py`

**Step 1: Write test for database connection**
```python
# tests/backend/api/test_glossary.py
from fastapi.testclient import TestClient
from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_glossary_empty():
    response = client.get("/api/glossary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_glossary_term():
    term_data = {
        "work_id": 1,
        "term": "Dragon",
        "translation": "Dragón",
        "is_proper_noun": True
    }
    response = client.post("/api/glossary", json=term_data)
    assert response.status_code == 201
```

**Step 2: Run test to verify current behavior**
Run: `pytest tests/backend/api/test_glossary.py -v`
Expected: Tests pass with in-memory mock

**Step 3: Refactor glossary routes to use repository**
```python
# src/pdftranslator/backend/api/routes/glossary.py
from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from pdftranslator.backend.api.models.schemas import GlossaryEntryResponse, GlossaryCreate, GlossaryUpdate
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.connection import DatabasePool

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


def get_glossary_repository() -> GlossaryRepository:
    pool = DatabasePool.get_instance().get_pool()
    return GlossaryRepository(pool)


@router.get("/", response_model=list[GlossaryEntryResponse])
async def list_glossary(
    work_id: Optional[int] = Query(None, description="Filter by work ID"),
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    if work_id:
        terms = repo.get_by_work(work_id)
    else:
        terms = repo.get_all()
    return [_term_to_response(t) for t in terms]


@router.post("/", response_model=GlossaryEntryResponse, status_code=201)
async def create_term(
    term_data: GlossaryCreate,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    term = repo.create(term_data.model_dump())
    return _term_to_response(term)


@router.get("/{term_id}", response_model=GlossaryEntryResponse)
async def get_term(
    term_id: int,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    term = repo.get_by_id(term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return _term_to_response(term)


@router.put("/{term_id}", response_model=GlossaryEntryResponse)
async def update_term(
    term_id: int,
    term_data: GlossaryUpdate,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    term = repo.update(term_id, term_data.model_dump(exclude_unset=True))
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return _term_to_response(term)


@router.delete("/{term_id}")
async def delete_term(
    term_id: int,
    repo: GlossaryRepository = Depends(get_glossary_repository),
):
    deleted = repo.delete(term_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Term not found")
    return {"message": "Term deleted", "id": term_id}


def _term_to_response(term) -> dict:
    return {
        "id": term.id,
        "work_id": term.work_id,
        "term": term.term,
        "translation": term.translation,
        "notes": term.notes,
        "is_proper_noun": term.is_proper_noun,
        "created_at": term.created_at,
    }
```

**Step 4: Add glossary schemas**
```python
# src/pdftranslator/backend/api/models/schemas.py
class GlossaryEntryResponse(BaseModel):
    id: int
    work_id: int
    term: str
    translation: Optional[str] = None
    notes: Optional[str] = None
    is_proper_noun: bool = False
    created_at: datetime


class GlossaryCreate(BaseModel):
    work_id: int
    term: str
    translation: Optional[str] = None
    notes: Optional[str] = None
    is_proper_noun: bool = False


class GlossaryUpdate(BaseModel):
    translation: Optional[str] = None
    notes: Optional[str] = None
    is_proper_noun: Optional[bool] = None
```

**Step 5: Run tests**
Run: `pytest tests/backend/api/test_glossary.py -v`
Expected: PASS (now using database)

**Step 6: Commit**
```bash
git add src/pdftranslator/backend/api/routes/glossary.py src/pdftranslator/backend/api/models/schemas.py tests/backend/api/test_glossary.py
git commit -m "refactor: connect Glossary API to database repository"
```

---

## Phase 6: Frontend - Remove Mock

### Task 7: Remove InMemoryWebApiModule

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/app.config.ts`
- Modify: `src/pdftranslator/frontend/src/environments/environment.ts`
- Modify: `src/pdftranslator/frontend/src/environments/environment.prod.ts`
- Delete: `src/pdftranslator/frontend/src/app/core/mock/in-memory-data.service.ts`
- Delete: `src/pdftranslator/frontend/src/app/core/mock/mock-data.ts`

**Step 1: Update app.config.ts to remove mock**
```typescript
// src/pdftranslator/frontend/src/app/app.config.ts
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

import { routes } from './app.routes';
import { apiInterceptor } from './core/interceptors/api.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([apiInterceptor])),
    provideAnimations()
  ]
};
```

**Step 2: Update environment.ts**
```typescript
// src/pdftranslator/frontend/src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  appName: 'PDFTranslator',
  version: '0.1.0'
};
```

**Step 3: Update environment.prod.ts**
```typescript
// src/pdftranslator/frontend/src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: '/api',
  appName: 'PDFTranslator',
  version: '0.1.0'
};
```

**Step 4: Delete mock files**
Run: `rm -rf src/pdftranslator/frontend/src/app/core/mock/`

**Step 5: Update api.interceptor to use environment**
```typescript
// src/pdftranslator/frontend/src/app/core/interceptors/api.interceptor.ts
import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export const apiInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const apiReq = req.clone({
    url: getApiUrl(req.url),
    withCredentials: true,
  });

  return next(apiReq);
};

function getApiUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const baseUrl = environment.apiUrl;
  
  if (url.startsWith('/api') || url.startsWith('api/')) {
    return url.startsWith('/') ? `${baseUrl}${url.replace('/api', '')}` : `${baseUrl}/${url.replace('api/', '')}`;
  }

  return `${baseUrl}/${url}`;
}
```

**Step 6: Build frontend**
Run: `cd src/pdftranslator/frontend && npx ng build --configuration development`
Expected: Build succeeds without errors

**Step 7: Commit**
```bash
git add src/pdftranslator/frontend/src/app/app.config.ts src/pdftranslator/frontend/src/environments/ src/pdftranslator/frontend/src/app/core/interceptors/api.interceptor.ts
git rm -r src/pdftranslator/frontend/src/app/core/mock/
git commit -m "refactor: remove InMemoryWebApi mock, connect to real backend"
```

---

## Phase 7: Frontend - Update Services

### Task 8: Update GlossaryService URL

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/core/services/glossary.service.ts`

**Step 1: Update service to use correct endpoint**
```typescript
// src/pdftranslator/frontend/src/app/core/services/glossary.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GlossaryTerm } from '../models/glossary-term.model';

@Injectable({
  providedIn: 'root'
})
export class GlossaryService {
  private http = inject(HttpClient);
  private apiUrl = '/api/glossary';

  getByWork(workId: number): Observable<GlossaryTerm[]> {
    return this.http.get<GlossaryTerm[]>(this.apiUrl, {
      params: { work_id: workId }
    });
  }

  create(term: Partial<GlossaryTerm>): Observable<GlossaryTerm> {
    return this.http.post<GlossaryTerm>(this.apiUrl, term);
  }

  update(id: number, term: Partial<GlossaryTerm>): Observable<GlossaryTerm> {
    return this.http.put<GlossaryTerm>(`${this.apiUrl}/${id}`, term);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 2: Commit**
```bash
git add src/pdftranslator/frontend/src/app/core/services/glossary.service.ts
git commit -m "fix: update GlossaryService to use correct API endpoint"
```

### Task 9: Update WorkService and VolumeService

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/core/services/work.service.ts`
- Modify: `src/pdftranslator/frontend/src/app/core/services/volume.service.ts`

**Step 1: Update WorkService**
```typescript
// src/pdftranslator/frontend/src/app/core/services/work.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Work } from '../models/work.model';

@Injectable({
  providedIn: 'root'
})
export class WorkService {
  private http = inject(HttpClient);
  private apiUrl = '/api/works';

  getAll(page: number = 1, pageSize: number = 20): Observable<{items: Work[], total: number}> {
    return this.http.get<{items: Work[], total: number}>(this.apiUrl, {
      params: { page, page_size: pageSize }
    });
  }

  getById(id: number): Observable<Work> {
    return this.http.get<Work>(`${this.apiUrl}/${id}`);
  }

  create(work: Partial<Work>): Observable<Work> {
    return this.http.post<Work>(this.apiUrl, work);
  }

  update(id: number, work: Partial<Work>): Observable<Work> {
    return this.http.put<Work>(`${this.apiUrl}/${id}`, work);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 2: Update VolumeService**
```typescript
// src/pdftranslator/frontend/src/app/core/services/volume.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Volume } from '../models/volume.model';

@Injectable({
  providedIn: 'root'
})
export class VolumeService {
  private http = inject(HttpClient);
  private apiUrl = '/api/volumes';

  getByWorkId(workId: number): Observable<Volume[]> {
    return this.http.get<Volume[]>(this.apiUrl, {
      params: { work_id: workId }
    });
  }

  getById(id: number): Observable<Volume> {
    return this.http.get<Volume>(`${this.apiUrl}/${id}`);
  }

  create(volume: Partial<Volume>): Observable<Volume> {
    return this.http.post<Volume>(this.apiUrl, volume);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 3: Commit**
```bash
git add src/pdftranslator/frontend/src/app/core/services/work.service.ts src/pdftranslator/frontend/src/app/core/services/volume.service.ts
git commit -m "refactor: update WorkService and VolumeService for real API"
```

---

## Phase 8: Integration Testing

### Task 10: End-to-End Verification

**Files:**
- None (manual testing)

**Step 1: Start backend**
Run: `python PDFAgent.py backend`
Expected: FastAPI running on http://localhost:8000

**Step 2: Start frontend**
Run: `cd src/pdftranslator/frontend && npm start`
Expected: Angular dev server running on http://localhost:4200

**Step 3: Verify database connection**
- Open http://localhost:4200
- Navigate to Files page
- Upload a PDF file
- Verify file appears in list (database-backed)

**Step 4: Verify works API**
- Navigate to Library page
- Verify works list loads from database
- Create new work
- Verify work appears in list

**Step 5: Verify glossary API**
- Navigate to Glossary page
- Add new term
- Verify term persists in database

**Step 6: Final commit**
```bash
git add -A
git commit -m "chore: final integration verification complete"
```

---

## Summary

This plan removes all mock data infrastructure and connects the Angular frontend to real FastAPI backend APIs backed by PostgreSQL + pgvector.

**Key Changes:**
1. Database: Docker Compose PostgreSQL with initialized schemas
2. Backend: New routes for Works, Volumes, Chapters; refactored Glossary to use DB
3. Frontend: Removed InMemoryWebApiModule, updated services to correct endpoints
4. Environment: Simplified configuration pointing to real backend

**Testing Strategy:**
- Unit tests for each API route
- Integration tests for service-to-repository connection
- Manual E2E verification of full flow

**Rollback Plan:**
If issues arise, revert to previous commit before Phase 6 (mock removal).
