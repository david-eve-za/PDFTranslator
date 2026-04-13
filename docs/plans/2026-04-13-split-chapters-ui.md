# Split Chapters UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a web UI for splitting volume text into chapters with interactive block markers.

**Architecture:** Frontend Angular component with textarea editor, marker insertion buttons, and preview modal. Backend FastAPI endpoint reuses existing `parse_blocks()` logic from CLI.

**Tech Stack:** Angular 17+, FastAPI, PostgreSQL, existing split_text.py parsing logic

---

## Task 1: Create Backend Split Endpoint

**Files:**
- Create: `src/pdftranslator/backend/api/routes/split.py`
- Modify: `src/pdftranslator/backend/api/routes/__init__.py`
- Modify: `src/pdftranslator/backend/api/models/schemas.py`

**Step 1: Add schemas to schemas.py**
```python
class SplitPreviewRequest(BaseModel):
    """Request schema for split preview."""
    text: str


class SplitPreviewResponse(BaseModel):
    """Response schema for split preview."""
    blocks: list[dict]
    has_errors: bool = False
    error_message: str | None = None


class SplitProcessRequest(BaseModel):
    """Request schema for split processing."""
    volume_id: int
    text: str


class SplitProcessResponse(BaseModel):
    """Response schema for split processing."""
    success: bool
    chapters_created: int = 0
    blocks: list[dict] = []
    error_message: str | None = None
```

**Step 2: Create split.py routes**
```python
"""Split text routes."""

from fastapi import APIRouter, Depends, HTTPException

from pdftranslator.backend.api.models.schemas import (
    SplitPreviewRequest,
    SplitPreviewResponse,
    SplitProcessRequest,
    SplitProcessResponse,
)
from pdftranslator.cli.commands.split_text import parse_blocks, BlockParseError
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository

router = APIRouter(prefix="/api/split", tags=["split"])


def get_volume_repository() -> VolumeRepository:
    return VolumeRepository(DatabasePool.get_instance())


def get_chapter_repository() -> ChapterRepository:
    return ChapterRepository(DatabasePool.get_instance())


@router.post("/preview", response_model=SplitPreviewResponse)
async def preview_split(request: SplitPreviewRequest):
    """Preview parsed blocks from text."""
    try:
        blocks = parse_blocks(request.text)
        block_dicts = [
            {
                "block_type": b.block_type,
                "title": b.title,
                "content": b.content,
                "start_line": b.start_line,
                "end_line": b.end_line,
            }
            for b in blocks
        ]
        return SplitPreviewResponse(blocks=block_dicts, has_errors=False)
    except BlockParseError as e:
        return SplitPreviewResponse(
            blocks=[],
            has_errors=True,
            error_message=f"Line {e.line_number}: {e.message}",
        )


@router.post("/process", response_model=SplitProcessResponse)
async def process_split(
    request: SplitProcessRequest,
    volume_repo: VolumeRepository = Depends(get_volume_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Process split text and create chapters."""
    volume = volume_repo.get_by_id(request.volume_id)
    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")

    try:
        blocks = parse_blocks(request.text)
    except BlockParseError as e:
        return SplitProcessResponse(
            success=False,
            error_message=f"Line {e.line_number}: {e.message}",
        )

    if not blocks:
        volume_repo.update_full_text(request.volume_id, request.text)
        return SplitProcessResponse(success=True, chapters_created=0)

    volume_repo.update_full_text(request.volume_id, request.text)

    existing_chapters = chapter_repo.get_by_volume(request.volume_id)
    for chapter in existing_chapters:
        if chapter.id:
            chapter_repo.delete(chapter.id)

    chapter_number = 1
    created_count = 0
    from pdftranslator.database.models import Chapter

    for block in blocks:
        if block.block_type == "Chapter":
            num = chapter_number
            chapter_number += 1
        else:
            num = None

        chapter = Chapter(
            id=None,
            volume_id=request.volume_id,
            chapter_number=num,
            title=block.title,
            original_text=block.content,
            translated_text=None,
        )
        chapter_repo.create(chapter)
        created_count += 1

    block_dicts = [
        {
            "block_type": b.block_type,
            "title": b.title,
            "content": b.content,
            "start_line": b.start_line,
            "end_line": b.end_line,
        }
        for b in blocks
    ]

    return SplitProcessResponse(
        success=True, chapters_created=created_count, blocks=block_dicts
    )
```

**Step 3: Register router in routes/__init__.py**
```python
from pdftranslator.backend.api.routes.split import router as split_router
# ... existing imports ...

# In create_app():
app.include_router(split_router)
```

**Step 4: Test endpoint manually**
Run: `python PDFAgent.py backend --reload`
Expected: Server starts, `/docs` shows new endpoints

**Step 5: Commit**
```bash
git add src/pdftranslator/backend/api/routes/split.py
git add src/pdftranslator/backend/api/models/schemas.py
git commit -m "feat(backend): add split preview and process endpoints"
```

---

## Task 2: Create Frontend Split Service

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/services/split.service.ts`

**Step 1: Create split.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ParsedBlock {
  block_type: string;
  title: string | null;
  content: string;
  start_line: number;
  end_line: number;
}

export interface SplitPreviewRequest {
  text: string;
}

export interface SplitPreviewResponse {
  blocks: ParsedBlock[];
  has_errors: boolean;
  error_message: string | null;
}

export interface SplitProcessRequest {
  volume_id: number;
  text: string;
}

export interface SplitProcessResponse {
  success: boolean;
  chapters_created: number;
  blocks: ParsedBlock[];
  error_message: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class SplitService {
  private apiUrl = '/api/split';

  constructor(private http: HttpClient) {}

  preview(text: string): Observable<SplitPreviewResponse> {
    return this.http.post<SplitPreviewResponse>(`${this.apiUrl}/preview`, { text });
  }

  process(volumeId: number, text: string): Observable<SplitProcessResponse> {
    return this.http.post<SplitProcessResponse>(`${this.apiUrl}/process`, {
      volume_id: volumeId,
      text
    });
  }
}
```

**Step 2: Commit**
```bash
git add src/pdftranslator/frontend/src/app/core/services/split.service.ts
git commit -m "feat(frontend): add split service for API communication"
```

---

## Task 3: Create Work and Volume Services

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/services/work.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/volume.service.ts`

**Step 1: Create work.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Work {
  id: number;
  title: string;
  title_translated: string | null;
  author: string;
  source_lang: string;
  target_lang: string;
  volumes: VolumeSummary[];
  created_at: string;
  updated_at: string;
}

export interface VolumeSummary {
  id: number;
  volume_number: number;
  title: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class WorkService {
  private apiUrl = '/api/works';

  constructor(private http: HttpClient) {}

  getAll(): Observable<Work[]> {
    return this.http.get<Work[]>(this.apiUrl);
  }

  getById(id: number): Observable<Work> {
    return this.http.get<Work>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 2: Create volume.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Volume {
  id: number;
  work_id: number;
  volume_number: number;
  title: string | null;
  full_text: string | null;
  chapters: ChapterSummary[];
  created_at: string;
}

export interface ChapterSummary {
  id: number;
  chapter_number: number | null;
  title: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class VolumeService {
  private apiUrl = '/api/volumes';

  constructor(private http: HttpClient) {}

  getByWorkId(workId: number): Observable<Volume[]> {
    return this.http.get<Volume[]>(`${this.apiUrl}?work_id=${workId}`);
  }

  getById(id: number): Observable<Volume> {
    return this.http.get<Volume>(`${this.apiUrl}/${id}`);
  }

  getFullText(id: number): Observable<{ text: string }> {
    return this.http.get<{ text: string }>(`${this.apiUrl}/${id}/full-text`);
  }
}
```

**Step 3: Commit**
```bash
git add src/pdftranslator/frontend/src/app/core/services/work.service.ts
git add src/pdftranslator/frontend/src/app/core/services/volume.service.ts
git commit -m "feat(frontend): add work and volume services"
```

---

## Task 4: Update Split Component TypeScript

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/features/split-chapters/split.component.ts`

**Step 1: Replace entire component content**
```typescript
import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkService, Work } from '../../core/services/work.service';
import { VolumeService, Volume } from '../../core/services/volume.service';
import { SplitService, ParsedBlock } from '../../core/services/split.service';

type BlockType = 'Prologue' | 'Chapter' | 'Epilogue';

@Component({
  selector: 'app-split',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './split.component.html',
  styleUrl: './split.component.scss'
})
export class SplitComponent implements OnInit {
  private workService = inject(WorkService);
  private volumeService = inject(VolumeService);
  private splitService = inject(SplitService);

  works = signal<Work[]>([]);
  volumes = signal<Volume[]>([]);
  selectedWorkId = signal<number | null>(null);
  selectedVolumeId = signal<number | null>(null);
  volumeText = signal('');
  parsedBlocks = signal<ParsedBlock[]>([]);
  
  isLoading = signal(false);
  isProcessing = signal(false);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);
  
  showTypeModal = signal(false);
  selectedBlockType = signal<BlockType>('Chapter');
  blockTitle = signal('');

  ngOnInit(): void {
    this.loadWorks();
  }

  private loadWorks(): void {
    this.isLoading.set(true);
    this.workService.getAll().subscribe({
      next: (works) => {
        this.works.set(works);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to load works');
        this.isLoading.set(false);
        console.error('Failed to load works:', err);
      }
    });
  }

  onWorkSelect(workId: string): void {
    const id = parseInt(workId, 10);
    if (isNaN(id)) {
      this.selectedWorkId.set(null);
      this.volumes.set([]);
      return;
    }
    
    this.selectedWorkId.set(id);
    this.selectedVolumeId.set(null);
    this.volumeText.set('');
    this.parsedBlocks.set([]);
    this.errorMessage.set(null);
    
    this.volumeService.getByWorkId(id).subscribe({
      next: (volumes) => {
        this.volumes.set(volumes.sort((a, b) => a.volume_number - b.volume_number));
      },
      error: (err) => {
        this.errorMessage.set('Failed to load volumes');
        console.error('Failed to load volumes:', err);
      }
    });
  }

  onVolumeSelect(volumeId: string): void {
    const id = parseInt(volumeId, 10);
    if (isNaN(id)) {
      this.selectedVolumeId.set(null);
      this.volumeText.set('');
      return;
    }
    
    this.selectedVolumeId.set(id);
    this.parsedBlocks.set([]);
    this.errorMessage.set(null);
    
    this.volumeService.getById(id).subscribe({
      next: (volume) => {
        this.volumeText.set(volume.full_text || '');
      },
      error: (err) => {
        this.errorMessage.set('Failed to load volume text');
        console.error('Failed to load volume:', err);
      }
    });
  }

  getCursorPosition(textarea: HTMLTextAreaElement): number {
    return textarea.selectionStart;
  }

  openTypeModal(): void {
    this.selectedBlockType.set('Chapter');
    this.blockTitle.set('');
    this.showTypeModal.set(true);
  }

  cancelTypeModal(): void {
    this.showTypeModal.set(false);
  }

  insertStartMarker(textarea: HTMLTextAreaElement): void {
    const position = this.getCursorPosition(textarea);
    const type = this.selectedBlockType();
    const title = this.blockTitle();
    
    let marker = `[===Type="${type}"`;
    if (title.trim()) {
      marker += ` Title="${title.trim()}"`;
    }
    marker += `===]\n`;
    
    const currentText = this.volumeText();
    const newText = currentText.slice(0, position) + marker + currentText.slice(position);
    this.volumeText.set(newText);
    
    this.showTypeModal.set(false);
    
    setTimeout(() => {
      textarea.focus();
      const newPosition = position + marker.length;
      textarea.setSelectionRange(newPosition, newPosition);
    }, 0);
  }

  insertEndMarker(textarea: HTMLTextAreaElement): void {
    const position = this.getCursorPosition(textarea);
    const marker = '\n[===End Block===]\n';
    
    const currentText = this.volumeText();
    const newText = currentText.slice(0, position) + marker + currentText.slice(position);
    this.volumeText.set(newText);
    
    setTimeout(() => {
      textarea.focus();
      const newPosition = position + marker.length;
      textarea.setSelectionRange(newPosition, newPosition);
    }, 0);
  }

  previewBlocks(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    
    this.splitService.preview(this.volumeText()).subscribe({
      next: (response) => {
        if (response.has_errors) {
          this.errorMessage.set(response.error_message || 'Parse error');
        } else {
          this.parsedBlocks.set(response.blocks);
        }
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to preview blocks');
        this.isLoading.set(false);
        console.error('Preview error:', err);
      }
    });
  }

  processAndSave(): void {
    const volumeId = this.selectedVolumeId();
    if (!volumeId) {
      this.errorMessage.set('No volume selected');
      return;
    }
    
    this.isProcessing.set(true);
    this.errorMessage.set(null);
    
    this.splitService.process(volumeId, this.volumeText()).subscribe({
      next: (response) => {
        if (response.success) {
          this.successMessage.set(`Successfully created ${response.chapters_created} chapter(s)`);
          this.parsedBlocks.set([]);
          setTimeout(() => this.successMessage.set(null), 5000);
        } else {
          this.errorMessage.set(response.error_message || 'Failed to process');
        }
        this.isProcessing.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to process split');
        this.isProcessing.set(false);
        console.error('Process error:', err);
      }
    });
  }

  clearPreview(): void {
    this.parsedBlocks.set([]);
  }

  getBlockTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      Prologue: '📜',
      Chapter: '📖',
      Epilogue: '🏁'
    };
    return icons[type] || '📄';
  }
}
```

**Step 2: Commit**
```bash
git add src/pdftranslator/frontend/src/app/features/split-chapters/split.component.ts
git commit -m "feat(frontend): implement split component with marker insertion"
```

---

## Task 5: Update Split Component HTML

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/features/split-chapters/split.component.html`

**Step 1: Replace entire HTML content**
```html
<div class="split-container">
  <header class="page-header">
    <h1 class="page-title">Split Chapters</h1>
    <p class="page-description">
      Divide volume text into chapters using block markers
    </p>
  </header>

  <main class="split-content">
    <section class="selectors-section">
      <div class="selector-group">
        <label class="form-label" for="work-select">Select Work</label>
        <select
          id="work-select"
          class="form-select"
          (change)="onWorkSelect($any($event.target).value)">
          <option value="">Choose a work...</option>
          @for (work of works(); track work.id) {
            <option [value]="work.id">{{ work.title }}</option>
          }
        </select>
      </div>

      @if (selectedWorkId()) {
        <div class="selector-group">
          <label class="form-label" for="volume-select">Select Volume</label>
          <select
            id="volume-select"
            class="form-select"
            (change)="onVolumeSelect($any($event.target).value)">
            <option value="">Choose a volume...</option>
            @for (volume of volumes(); track volume.id) {
              <option [value]="volume.id">Volume {{ volume.volume_number }}</option>
            }
          </select>
        </div>
      }
    </section>

    @if (selectedVolumeId()) {
      <section class="editor-section">
        <div class="editor-header">
          <h3>Volume Text</h3>
          <div class="format-help">
            <p>Markers:</p>
            <code>[===Type="Prologue"===]</code>
            <code>[===Type="Chapter" Title="..."===]</code>
            <code>[===Type="Epilogue"===]</code>
            <code>[===End Block===]</code>
          </div>
        </div>

        <div class="editor-actions">
          <button class="btn btn-primary" (click)="openTypeModal()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Add Start Marker
          </button>
          <button class="btn btn-secondary" (click)="insertEndMarker(textareaRef)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            </svg>
            Add End Marker
          </button>
        </div>

        <textarea
          #textareaRef
          class="text-editor"
          [(ngModel)]="volumeText"
          rows="20"
          placeholder="Volume text will appear here...">
        </textarea>

        <div class="process-actions">
          <button
            class="btn btn-outline"
            (click)="previewBlocks()"
            [disabled]="isLoading() || !volumeText()">
            @if (isLoading()) {
              Previewing...
            } @else {
              Preview Blocks
            }
          </button>
        </div>
      </section>
    }

    @if (parsedBlocks().length > 0) {
      <section class="preview-section">
        <div class="preview-header">
          <h3>Detected Blocks ({{ parsedBlocks().length }})</h3>
          <button class="btn btn-ghost" (click)="clearPreview()">Clear</button>
        </div>

        <div class="blocks-list">
          @for (block of parsedBlocks(); track $index) {
            <div class="block-item">
              <div class="block-icon">{{ getBlockTypeIcon(block.block_type) }}</div>
              <div class="block-info">
                <h4>{{ block.title || block.block_type }}</h4>
                <p class="block-type">{{ block.block_type }}</p>
                <p class="block-lines">Lines {{ block.start_line }} - {{ block.end_line }}</p>
              </div>
              <span class="block-number">#{{ $index + 1 }}</span>
            </div>
          }
        </div>

        <div class="confirm-actions">
          <button
            class="btn btn-success"
            (click)="processAndSave()"
            [disabled]="isProcessing()">
            @if (isProcessing()) {
              Processing...
            } @else {
              Confirm & Save
            }
          </button>
          <button class="btn btn-secondary" (click)="clearPreview()">Cancel</button>
        </div>
      </section>
    }

    @if (errorMessage()) {
      <div class="error-message">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span>{{ errorMessage() }}</span>
      </div>
    }

    @if (successMessage()) {
      <div class="success-message">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9 12l2 2 4-4"/>
        </svg>
        <span>{{ successMessage() }}</span>
      </div>
    }
  </main>

  @if (showTypeModal()) {
    <div class="modal-overlay" (click)="cancelTypeModal()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>Add Block Start Marker</h3>
          <button class="modal-close" (click)="cancelTypeModal()">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Block Type</label>
            <select class="form-select" [(ngModel)]="selectedBlockType">
              <option value="Prologue">Prologue</option>
              <option value="Chapter">Chapter</option>
              <option value="Epilogue">Epilogue</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Title (Optional)</label>
            <input
              type="text"
              class="form-input"
              [(ngModel)]="blockTitle"
              placeholder="Chapter title..." />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" (click)="cancelTypeModal()">Cancel</button>
          <button class="btn btn-primary" (click)="insertStartMarker(textareaRef)">
            Insert Marker
          </button>
        </div>
      </div>
    </div>
  }
</div>
```

**Step 2: Commit**
```bash
git add src/pdftranslator/frontend/src/app/features/split-chapters/split.component.html
git commit -m "feat(frontend): add split component HTML with modal and actions"
```

---

## Task 6: Update Split Component Styles

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/features/split-chapters/split.component.scss`

**Step 1: Replace entire SCSS content**
```scss
.split-container {
  max-width: 1200px;
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

.split-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.selectors-section {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.selector-group {
  flex: 1;
  min-width: 200px;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-select,
.form-input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: var(--bg-primary, #fff);

  &:focus {
    outline: none;
    border-color: var(--primary, #3b82f6);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
}

.editor-section {
  background: var(--bg-secondary, #f9fafb);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;

  h3 {
    margin: 0;
    font-size: 1.125rem;
  }

  .format-help {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);

    p {
      margin: 0;
    }

    code {
      background: var(--bg-primary, #fff);
      padding: 0.125rem 0.375rem;
      border-radius: 0.25rem;
      font-family: monospace;
      font-size: 0.6875rem;
    }
  }
}

.editor-actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.text-editor {
  width: 100%;
  min-height: 400px;
  padding: 1rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.5rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  resize: vertical;
  background: var(--bg-primary, #fff);

  &:focus {
    outline: none;
    border-color: var(--primary, #3b82f6);
  }
}

.process-actions {
  margin-top: 1rem;
}

.preview-section {
  background: var(--bg-secondary, #f9fafb);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  h3 {
    margin: 0;
  }
}

.blocks-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.block-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-primary, #fff);
  border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e5e7eb);
}

.block-icon {
  font-size: 1.5rem;
}

.block-info {
  flex: 1;

  h4 {
    margin: 0 0 0.25rem;
    font-size: 0.875rem;
  }

  .block-type {
    margin: 0;
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
    text-transform: capitalize;
  }

  .block-lines {
    margin: 0;
    font-size: 0.6875rem;
    color: var(--text-tertiary, #9ca3af);
  }
}

.block-number {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.error-message,
.success-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border-radius: 0.5rem;
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

// Buttons
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;

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

.btn-success {
  background: #16a34a;
  color: white;

  &:hover:not(:disabled) {
    background: #15803d;
  }
}

.btn-outline {
  background: transparent;
  color: var(--primary, #3b82f6);
  border: 1px solid var(--primary, #3b82f6);

  &:hover:not(:disabled) {
    background: var(--primary, #3b82f6);
    color: white;
  }
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary, #6b7280);

  &:hover:not(:disabled) {
    color: var(--text-primary, #111827);
  }
}

// Modal
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
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);

  h3 {
    margin: 0;
    font-size: 1rem;
  }

  .modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-secondary, #6b7280);
    line-height: 1;

    &:hover {
      color: var(--text-primary, #111827);
    }
  }
}

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

.form-group {
  label {
    display: block;
    margin-bottom: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
  }
}
```

**Step 2: Commit**
```bash
git add src/pdftranslator/frontend/src/app/features/split-chapters/split.component.scss
git commit -m "feat(frontend): add split component styles"
```

---

## Task 7: Register Backend Router

**Files:**
- Modify: `src/pdftranslator/backend/api/routes/__init__.py`

**Step 1: Add split router to routes/__init__.py**
Locate the file and add the import and router registration:
```python
from pdftranslator.backend.api.routes.split import router as split_router

# In create_app function, add:
app.include_router(split_router)
```

**Step 2: Commit**
```bash
git add src/pdftranslator/backend/api/routes/__init__.py
git commit -m "feat(backend): register split router in API"
```

---

## Task 8: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `AGENTS.md`
- Modify: `pyproject.toml`

**Step 1: Update README.md - Add Split Chapters section**
Add after existing features section:
```markdown
### Split Chapters Feature

The Split Chapters feature allows you to divide volume text into chapters using an interactive web interface:

1. **Select Work & Volume**: Choose a work and volume from your library
2. **Mark Blocks**: Use the interactive editor to insert block markers:
   - `[===Type="Prologue"===]` - Start of a prologue
   - `[===Type="Chapter" Title="Chapter Name"===]` - Start of a chapter
   - `[===Type="Epilogue"===]` - Start of an epilogue
   - `[===End Block===]` - End of any block
3. **Preview**: Preview detected blocks before saving
4. **Process**: Confirm to create chapters in the database

#### API Endpoints

- `POST /api/split/preview` - Preview parsed blocks from text
- `POST /api/split/process` - Process text and create chapters
```

**Step 2: Update CHANGELOG.md**
```markdown
## [Unreleased]

### Added
- Split Chapters UI: Interactive web interface for dividing volumes into chapters
  - Block marker insertion with type selection (Prologue, Chapter, Epilogue)
  - Preview parsed blocks before processing
  - Backend endpoints: `/api/split/preview`, `/api/split/process`
- Glossary UI: Full glossary management interface matching backend schema
  - Added `entity_type`, `context`, `frequency`, `source_lang`, `target_lang` fields

### Fixed
- Glossary frontend-backend schema mismatch (notes → context, added entity_type, etc.)
```

**Step 3: Update AGENTS.md**
Add to the project structure section and relevant sections.

**Step 4: Update pyproject.toml version**
Bump version if needed.

**Step 5: Commit**
```bash
git add README.md CHANGELOG.md AGENTS.md pyproject.toml
git commit -m "docs: update documentation for split chapters feature"
```

---

## Task 9: Final Commit and Summary

**Step 1: Run tests if available**
```bash
pytest tests/ -v --tb=short || true
```

**Step 2: Create final commit**
```bash
git add -A
git commit -m "feat: implement split chapters UI with block markers

- Add backend endpoints for split preview and processing
- Create frontend split component with marker insertion
- Add work and volume services for data loading
- Implement preview and confirmation flow
- Update documentation (README, CHANGELOG, AGENTS.md)"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-04-13-split-chapters-ui.md`.**

Two execution options:

**1. Subagent-Driven (this session)**
- I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)**
- Open new session with executing-plans, batch execution with checkpoints

Which approach?
