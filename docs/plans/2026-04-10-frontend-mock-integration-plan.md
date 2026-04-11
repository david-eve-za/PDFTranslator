# Frontend Mock Data Integration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace current basic Angular frontend with feature-rich application using InMemoryWebAPI for mock data, implementing 5 core features that mirror CLI functionality.

**Architecture:** Feature-based modules (Dashboard, Library, Translate, Glossary, Split Chapters) with shared components. Uses Angular InMemoryWebAPI for realistic mock data during development, enabling easy transition to real backend later.

**Tech Stack:** Angular 17+, TypeScript, SCSS, Angular InMemoryWebAPI, Chart.js, Angular Material

---

## Prerequisites

- Branch created: `feature/frontend-mock-data`
- Angular CLI installed
- Node.js 18+ available

---

## Phase 1: Core Setup

### Task 1.1: Install Dependencies

**Files:**
- Modify: `src/pdftranslator/frontend/package.json`

**Step 1: Install Angular InMemoryWebAPI and Chart.js**
```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator/src/pdftranslator/frontend
npm install angular-in-memory-web-api@0.17.0 --save
npm install chart.js@4.4.0 ng2-charts@5.0.0 --save
npm install @angular/material@17.0.0 --save
```

**Step 2: Verify installation**
Run: `npm list angular-in-memory-web-api chart.js ng2-charts`
Expected: Versions displayed without errors

**Step 3: Commit**
```bash
git add package.json package-lock.json
git commit -m "chore: install InMemoryWebAPI, Chart.js, and Angular Material"
```

---

### Task 1.2: Create Core Models

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/models/work.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/volume.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/chapter.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/glossary-term.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/translation-progress.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/dashboard.model.ts`
- Create: `src/pdftranslator/frontend/src/app/core/models/index.ts`

**Step 1: Create Work model**
File: `src/app/core/models/work.model.ts`
```typescript
export interface Work {
  id: number;
  title: string;
  title_translated?: string;
  author: string;
  volumes: Volume[];
  total_chapters: number;
  translated_chapters: number;
  created_at: Date;
  updated_at: Date;
}

export interface WorkCreate {
  title: string;
  author: string;
}

export interface WorkUpdate {
  title?: string;
  title_translated?: string;
  author?: string;
}
```

**Step 2: Create Volume model**
File: `src/app/core/models/volume.model.ts`
```typescript
export interface Volume {
  id: number;
  work_id: number;
  volume_number: number;
  chapters: Chapter[];
  full_text?: string;
  translated_text?: string;
  created_at: Date;
}

export interface VolumeCreate {
  work_id: number;
  volume_number: number;
  full_text?: string;
}
```

**Step 3: Create Chapter model**
File: `src/app/core/models/chapter.model.ts`
```typescript
export type ChapterType = 'prologue' | 'chapter' | 'epilogue';
export type TranslationStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface Chapter {
  id: number;
  volume_id: number;
  chapter_number: number;
  title: string;
  chapter_type: ChapterType;
  original_text?: string;
  translated_text?: string;
  is_translated: boolean;
  start_position?: number;
  end_position?: number;
  created_at: Date;
  updated_at: Date;
}

export interface ChapterCreate {
  volume_id: number;
  chapter_number: number;
  title: string;
  chapter_type: ChapterType;
  original_text?: string;
}
```

**Step 4: Create Glossary Term model**
File: `src/app/core/models/glossary-term.model.ts`
```typescript
export type EntityType = 'character' | 'place' | 'skill' | 'item' | 'spell' | 'faction' | 'title' | 'race' | 'other';

export interface GlossaryTerm {
  id: number;
  work_id: number;
  term: string;
  translation?: string;
  entity_type: EntityType;
  context?: string;
  is_proper_noun: boolean;
  frequency: number;
  source_lang: string;
  target_lang: string;
  created_at: Date;
  updated_at: Date;
}

export interface GlossaryTermCreate {
  work_id: number;
  term: string;
  translation?: string;
  entity_type: EntityType;
  context?: string;
  is_proper_noun: boolean;
  source_lang: string;
  target_lang: string;
}

export interface GlossaryTermUpdate {
  term?: string;
  translation?: string;
  entity_type?: EntityType;
  context?: string;
  is_proper_noun?: boolean;
}
```

**Step 5: Create Translation Progress model**
File: `src/app/core/models/translation-progress.model.ts`
```typescript
export type TranslationScope = 'all_book' | 'all_volume' | 'single_chapter';
export type ProgressStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface TranslationProgress {
  id: string;
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  status: ProgressStatus;
  total_chunks: number;
  completed_chunks: number;
  current_chunk?: string;
  started_at?: Date;
  completed_at?: Date;
  error?: string;
}

export interface TranslationStartRequest {
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  source_lang: string;
  target_lang: string;
  provider: string;
}
```

**Step 6: Create Dashboard models**
File: `src/app/core/models/dashboard.model.ts`
```typescript
export interface DashboardStats {
  total_works: number;
  total_glossary_terms: number;
  translations_this_week: number;
  average_progress: number;
}

export interface RecentActivity {
  id: string;
  type: 'translation' | 'glossary' | 'import' | 'split';
  action: string;
  work_title?: string;
  timestamp: Date;
}

export interface TranslationChartData {
  completed: number;
  in_progress: number;
  pending: number;
}
```

**Step 7: Create index barrel export**
File: `src/app/core/models/index.ts`
```typescript
export * from './work.model';
export * from './volume.model';
export * from './chapter.model';
export * from './glossary-term.model';
export * from './translation-progress.model';
export * from './dashboard.model';
```

**Step 8: Commit**
```bash
git add src/app/core/models/
git commit -m "feat: add core models for all entities"
```

---

### Task 1.3: Create Mock Data

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/mock/mock-data.ts`
- Create: `src/pdftranslator/frontend/src/app/core/mock/in-memory-data.service.ts`

**Step 1: Create mock data constants**
File: `src/app/core/mock/mock-data.ts`
```typescript
import { Work, Volume, Chapter, GlossaryTerm, TranslationProgress, RecentActivity } from '../models';

export const MOCK_WORKS: Work[] = [
  {
    id: 1,
    title: 'The Great Adventure',
    title_translated: 'La Gran Aventura',
    author: 'John Smith',
    volumes: [],
    total_chapters: 45,
    translated_chapters: 30,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-03-20')
  },
  {
    id: 2,
    title: 'Mystery of the Ancients',
    author: 'Jane Doe',
    volumes: [],
    total_chapters: 60,
    translated_chapters: 0,
    created_at: new Date('2025-02-10'),
    updated_at: new Date('2026-04-01')
  },
  {
    id: 3,
    title: 'Dragon\'s Legacy',
    title_translated: 'El Legado del Dragón',
    author: 'Carlos Writer',
    volumes: [],
    total_chapters: 120,
    translated_chapters: 120,
    created_at: new Date('2024-12-01'),
    updated_at: new Date('2026-02-28')
  }
];

export const MOCK_VOLUMES: Volume[] = [
  {
    id: 1,
    work_id: 1,
    volume_number: 1,
    chapters: [],
    full_text: 'Volume 1 full text...',
    created_at: new Date('2025-01-15')
  },
  {
    id: 2,
    work_id: 1,
    volume_number: 2,
    chapters: [],
    full_text: 'Volume 2 full text...',
    created_at: new Date('2025-01-20')
  },
  {
    id: 3,
    work_id: 2,
    volume_number: 1,
    chapters: [],
    created_at: new Date('2025-02-10')
  },
  {
    id: 4,
    work_id: 3,
    volume_number: 1,
    chapters: [],
    full_text: 'Dragon\'s Legacy Vol 1...',
    created_at: new Date('2024-12-01')
  },
  {
    id: 5,
    work_id: 3,
    volume_number: 2,
    chapters: [],
    full_text: 'Dragon\'s Legacy Vol 2...',
    created_at: new Date('2024-12-15')
  }
];

export const MOCK_CHAPTERS: Chapter[] = [
  {
    id: 1,
    volume_id: 1,
    chapter_number: 0,
    title: 'Prologue',
    chapter_type: 'prologue',
    original_text: 'In the beginning...',
    translated_text: 'Al principio...',
    is_translated: true,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-01-10')
  },
  {
    id: 2,
    volume_id: 1,
    chapter_number: 1,
    title: 'The Journey Begins',
    chapter_type: 'chapter',
    original_text: 'Chapter 1 content...',
    translated_text: 'Capítulo 1 contenido...',
    is_translated: true,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-01-12')
  },
  {
    id: 3,
    volume_id: 1,
    chapter_number: 2,
    title: 'Into the Forest',
    chapter_type: 'chapter',
    original_text: 'Chapter 2 content...',
    is_translated: false,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2025-01-15')
  },
  {
    id: 4,
    volume_id: 2,
    chapter_number: 1,
    title: 'New Horizons',
    chapter_type: 'chapter',
    original_text: 'Chapter 1 of vol 2...',
    is_translated: false,
    created_at: new Date('2025-01-20'),
    updated_at: new Date('2025-01-20')
  },
  {
    id: 5,
    volume_id: 3,
    chapter_number: 1,
    title: 'The First Mystery',
    chapter_type: 'chapter',
    original_text: 'Mystery chapter 1...',
    is_translated: false,
    created_at: new Date('2025-02-10'),
    updated_at: new Date('2025-02-10')
  }
];

export const MOCK_GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    id: 1,
    work_id: 1,
    term: 'Elena',
    translation: 'Elena',
    entity_type: 'character',
    context: 'Main protagonist',
    is_proper_noun: true,
    frequency: 150,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-15')
  },
  {
    id: 2,
    work_id: 1,
    term: 'Crystal Kingdom',
    translation: 'Reino de Cristal',
    entity_type: 'place',
    context: 'Main setting',
    is_proper_noun: true,
    frequency: 80,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-15')
  },
  {
    id: 3,
    work_id: 1,
    term: 'Fireball',
    translation: 'Bola de fuego',
    entity_type: 'spell',
    context: 'Common fire spell',
    is_proper_noun: false,
    frequency: 45,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-20')
  },
  {
    id: 4,
    work_id: 1,
    term: 'Shadow Guild',
    translation: 'Gremio de las Sombras',
    entity_type: 'faction',
    context: 'Antagonist group',
    is_proper_noun: true,
    frequency: 60,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-18')
  },
  {
    id: 5,
    work_id: 2,
    term: 'Ancient Temple',
    translation: 'Templo Ancestral',
    entity_type: 'place',
    context: 'Central location',
    is_proper_noun: true,
    frequency: 90,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-15'),
    updated_at: new Date('2025-02-15')
  }
];

export const MOCK_TRANSLATION_PROGRESS: TranslationProgress[] = [
  {
    id: 'trans-1',
    work_id: 1,
    scope: 'all_volume',
    volume_id: 1,
    status: 'in_progress',
    total_chunks: 150,
    completed_chunks: 45,
    current_chunk: 'Chapter 2, paragraph 12',
    started_at: new Date('2026-04-10T10:00:00'),
  }
];

export const MOCK_RECENT_ACTIVITIES: RecentActivity[] = [
  {
    id: 'act-1',
    type: 'translation',
    action: 'Translation completed',
    work_title: 'Dragon\'s Legacy',
    timestamp: new Date('2026-04-10T14:30:00')
  },
  {
    id: 'act-2',
    type: 'glossary',
    action: 'Term added: Shadow Guild',
    work_title: 'The Great Adventure',
    timestamp: new Date('2026-04-10T13:15:00')
  },
  {
    id: 'act-3',
    type: 'import',
    action: 'Work imported',
    work_title: 'Mystery of the Ancients',
    timestamp: new Date('2026-04-09T16:00:00')
  },
  {
    id: 'act-4',
    type: 'split',
    action: 'Chapters split',
    work_title: 'The Great Adventure - Vol 1',
    timestamp: new Date('2026-04-09T10:30:00')
  },
  {
    id: 'act-5',
    type: 'translation',
    action: 'Translation started',
    work_title: 'The Great Adventure',
    timestamp: new Date('2026-04-10T10:00:00')
  }
];
```

**Step 2: Create InMemoryDataService**
File: `src/app/core/mock/in-memory-data.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { InMemoryDbService } from 'angular-in-memory-web-api';
import {
  MOCK_WORKS,
  MOCK_VOLUMES,
  MOCK_CHAPTERS,
  MOCK_GLOSSARY_TERMS,
  MOCK_TRANSLATION_PROGRESS,
  MOCK_RECENT_ACTIVITIES
} from './mock-data';

@Injectable({
  providedIn: 'root'
})
export class InMemoryDataService implements InMemoryDbService {
  createDb() {
    return {
      works: MOCK_WORKS,
      volumes: MOCK_VOLUMES,
      chapters: MOCK_CHAPTERS,
      glossaryTerms: MOCK_GLOSSARY_TERMS,
      translationProgress: MOCK_TRANSLATION_PROGRESS,
      recentActivities: MOCK_RECENT_ACTIVITIES
    };
  }

  genId<T>(collection: T[]): number {
    return collection.length > 0 ? Math.max(...collection.map((item: any) => item.id)) + 1 : 1;
  }
}
```

**Step 3: Commit**
```bash
git add src/app/core/mock/
git commit -m "feat: add mock data and InMemoryDataService"
```

---

### Task 1.4: Configure InMemoryWebAPI

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/app.config.ts`

**Step 1: Import and configure InMemoryWebAPI**
Update `app.config.ts`:
```typescript
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { InMemoryWebApiModule } from 'angular-in-memory-web-api';

import { routes } from './app.routes';
import { InMemoryDataService } from './core/mock/in-memory-data.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(),
    InMemoryWebApiModule.forRoot(InMemoryDataService, { delay: 500 })
  ]
};
```

**Step 2: Verify configuration**
Run: `npm run build`
Expected: Build successful

**Step 3: Commit**
```bash
git add src/app/app.config.ts
git commit -m "feat: configure InMemoryWebAPI for mock data"
```

---

### Task 1.5: Create Core Services

**Files:**
- Create: `src/pdftranslator/frontend/src/app/core/services/work.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/volume.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/chapter.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/glossary.service.ts`
- Create: `src/pdftranslator/frontend/src/app/core/services/dashboard.service.ts`

**Step 1: Create WorkService**
File: `src/app/core/services/work.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Work, WorkCreate, WorkUpdate } from '../models';

@Injectable({
  providedIn: 'root'
})
export class WorkService {
  private apiUrl = 'api/works';

  constructor(private http: HttpClient) {}

  getAll(): Observable<Work[]> {
    return this.http.get<Work[]>(this.apiUrl);
  }

  getById(id: number): Observable<Work> {
    return this.http.get<Work>(`${this.apiUrl}/${id}`);
  }

  create(work: WorkCreate): Observable<Work> {
    return this.http.post<Work>(this.apiUrl, work);
  }

  update(id: number, work: WorkUpdate): Observable<Work> {
    return this.http.put<Work>(`${this.apiUrl}/${id}`, work);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 2: Create VolumeService**
File: `src/app/core/services/volume.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Volume, VolumeCreate } from '../models';

@Injectable({
  providedIn: 'root'
})
export class VolumeService {
  private apiUrl = 'api/volumes';

  constructor(private http: HttpClient) {}

  getByWorkId(workId: number): Observable<Volume[]> {
    return this.http.get<Volume[]>(`${this.apiUrl}?work_id=${workId}`);
  }

  getById(id: number): Observable<Volume> {
    return this.http.get<Volume>(`${this.apiUrl}/${id}`);
  }

  create(volume: VolumeCreate): Observable<Volume> {
    return this.http.post<Volume>(this.apiUrl, volume);
  }
}
```

**Step 3: Create ChapterService**
File: `src/app/core/services/chapter.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Chapter, ChapterCreate } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ChapterService {
  private apiUrl = 'api/chapters';

  constructor(private http: HttpClient) {}

  getByVolumeId(volumeId: number): Observable<Chapter[]> {
    return this.http.get<Chapter[]>(`${this.apiUrl}?volume_id=${volumeId}`);
  }

  getById(id: number): Observable<Chapter> {
    return this.http.get<Chapter>(`${this.apiUrl}/${id}`);
  }

  create(chapter: ChapterCreate): Observable<Chapter> {
    return this.http.post<Chapter>(this.apiUrl, chapter);
  }

  update(id: number, chapter: Partial<Chapter>): Observable<Chapter> {
    return this.http.put<Chapter>(`${this.apiUrl}/${id}`, chapter);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 4: Create GlossaryService**
File: `src/app/core/services/glossary.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GlossaryTerm, GlossaryTermCreate, GlossaryTermUpdate, EntityType } from '../models';

@Injectable({
  providedIn: 'root'
})
export class GlossaryService {
  private apiUrl = 'api/glossaryTerms';

  constructor(private http: HttpClient) {}

  getAll(workId?: number, entityType?: EntityType): Observable<GlossaryTerm[]> {
    let params = new HttpParams();
    if (workId) params = params.set('work_id', workId.toString());
    if (entityType) params = params.set('entity_type', entityType);
    return this.http.get<GlossaryTerm[]>(this.apiUrl, { params });
  }

  getById(id: number): Observable<GlossaryTerm> {
    return this.http.get<GlossaryTerm>(`${this.apiUrl}/${id}`);
  }

  create(term: GlossaryTermCreate): Observable<GlossaryTerm> {
    return this.http.post<GlossaryTerm>(this.apiUrl, term);
  }

  update(id: number, term: GlossaryTermUpdate): Observable<GlossaryTerm> {
    return this.http.put<GlossaryTerm>(`${this.apiUrl}/${id}`, term);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
```

**Step 5: Create DashboardService**
File: `src/app/core/services/dashboard.service.ts`
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DashboardStats, RecentActivity } from '../models';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private apiUrl = 'api';

  constructor(private http: HttpClient) {}

  getStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.apiUrl}/works/stats`);
  }

  getRecentActivities(): Observable<RecentActivity[]> {
    return this.http.get<RecentActivity[]>(`${this.apiUrl}/recentActivities`);
  }
}
```

**Step 6: Commit**
```bash
git add src/app/core/services/
git commit -m "feat: add core services for API communication"
```

---

### Task 1.6: Update App Routing

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/app.routes.ts`

**Step 1: Update routing structure**
Update `app.routes.ts`:
```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'library',
    loadChildren: () =>
      import('./features/library/library.routes').then(m => m.libraryRoutes)
  },
  {
    path: 'translate',
    loadChildren: () =>
      import('./features/translate/translate.routes').then(m => m.translateRoutes)
  },
  {
    path: 'glossary',
    loadChildren: () =>
      import('./features/glossary/glossary.routes').then(m => m.glossaryRoutes)
  },
  {
    path: 'split',
    loadChildren: () =>
      import('./features/split-chapters/split.routes').then(m => m.splitRoutes)
  },
  {
    path: '**',
    redirectTo: '/dashboard'
  }
];
```

**Step 2: Commit**
```bash
git add src/app/app.routes.ts
git commit -m "feat: update app routing with lazy-loaded feature modules"
```

---

### Task 1.7: Update App Component and Styles

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/app.ts`
- Modify: `src/pdftranslator/frontend/src/app/app.html`
- Modify: `src/pdftranslator/frontend/src/app/app.scss`
- Modify: `src/pdftranslator/frontend/src/styles.scss`

**Step 1: Update app.ts with navigation**
```typescript
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = 'PDFTranslator';
  protected readonly currentTheme = signal<'light' | 'dark'>('light');
  protected readonly menuOpen = signal(false);

  constructor(private themeService: ThemeService) {
    this.currentTheme.set(this.themeService.getCurrentTheme());
  }

  toggleTheme() {
    const newTheme = this.currentTheme() === 'light' ? 'dark' : 'light';
    this.themeService.setTheme(newTheme);
    this.currentTheme.set(newTheme);
  }

  toggleMenu() {
    this.menuOpen.update(v => !v);
  }
}
```

**Step 2: Update app.html with navigation**
```html
<div class="app-container" [attr.data-theme]="currentTheme()">
  <header class="app-header">
    <div class="header-content">
      <a routerLink="/dashboard" class="logo">
        <h1>{{ title }}</h1>
      </a>

      <button class="menu-toggle" (click)="toggleMenu()" [class.active]="menuOpen()">
        <span></span>
        <span></span>
        <span></span>
      </button>

      <nav class="nav-menu" [class.open]="menuOpen()">
        <a routerLink="/dashboard" routerLinkActive="active" (click)="menuOpen.set(false)">
          Dashboard
        </a>
        <a routerLink="/library" routerLinkActive="active" (click)="menuOpen.set(false)">
          Library
        </a>
        <a routerLink="/translate" routerLinkActive="active" (click)="menuOpen.set(false)">
          Translate
        </a>
        <a routerLink="/glossary" routerLinkActive="active" (click)="menuOpen.set(false)">
          Glossary
        </a>
        <a routerLink="/split" routerLinkActive="active" (click)="menuOpen.set(false)">
          Split Chapters
        </a>
      </nav>

      <button class="theme-toggle" (click)="toggleTheme()" [attr.aria-label]="'Toggle theme'">
        @if (currentTheme() === 'light') {
          🌙
        } @else {
          ☀️
        }
      </button>
    </div>
  </header>

  <main class="app-main">
    <router-outlet></router-outlet>
  </main>

  <footer class="app-footer">
    <p>&copy; 2026 PDFTranslator. All rights reserved.</p>
  </footer>
</div>
```

**Step 3: Update app.scss**
```scss
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--background);
  color: var(--text);
  transition: background-color 0.3s, color 0.3s;
}

.app-header {
  background-color: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
  }

  .logo {
    text-decoration: none;
    color: var(--text);

    h1 {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      font-size: 1.5rem;
      font-weight: 700;
    }
  }

  .menu-toggle {
    display: none;
    flex-direction: column;
    gap: 5px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;

    span {
      width: 25px;
      height: 3px;
      background-color: var(--text);
      transition: transform 0.3s;
    }

    &.active span:nth-child(1) {
      transform: rotate(45deg) translate(5px, 5px);
    }

    &.active span:nth-child(2) {
      opacity: 0;
    }

    &.active span:nth-child(3) {
      transform: rotate(-45deg) translate(7px, -6px);
    }
  }

  .nav-menu {
    display: flex;
    gap: 2rem;

    a {
      text-decoration: none;
      color: var(--text-secondary);
      font-weight: 500;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      transition: all 0.2s;

      &:hover {
        color: var(--primary);
        background-color: var(--background);
      }

      &.active {
        color: var(--primary);
        background-color: var(--primary-light);
        background-color: rgba(99, 102, 241, 0.1);
      }
    }
  }

  .theme-toggle {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 8px;
    transition: background-color 0.2s;

    &:hover {
      background-color: var(--background);
    }
  }

  @media (max-width: 768px) {
    .menu-toggle {
      display: flex;
    }

    .nav-menu {
      position: fixed;
      top: 70px;
      left: 0;
      right: 0;
      background-color: var(--surface);
      flex-direction: column;
      padding: 2rem;
      gap: 1rem;
      transform: translateY(-100%);
      opacity: 0;
      transition: transform 0.3s, opacity 0.3s;
      border-bottom: 1px solid var(--border);

      &.open {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .theme-toggle {
      margin-left: auto;
    }
  }
}

.app-main {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem;
}

.app-footer {
  background-color: var(--surface);
  border-top: 1px solid var(--border);
  padding: 1.5rem 2rem;
  text-align: center;

  p {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.875rem;
  }
}
```

**Step 4: Update global styles.scss**
```scss
/* Global Styles */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  /* Primary colors */
  --primary: #6366f1;
  --primary-light: #818cf8;
  --primary-dark: #4f46e5;
  
  /* Accent colors */
  --accent: #f59e0b;
  --accent-light: #fbbf24;
  
  /* Status colors */
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
  
  /* Neutral colors - Light theme */
  --background: #f8fafc;
  --surface: #ffffff;
  --text: #1e293b;
  --text-secondary: #64748b;
  --border: #e2e8f0;
}

[data-theme="dark"] {
  --background: #0f172a;
  --surface: #1e293b;
  --text: #f1f5f9;
  --text-secondary: #94a3b8;
  --border: #334155;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  line-height: 1.6;
  background-color: var(--background);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }
h4 { font-size: 1.25rem; }

code, pre {
  font-family: 'JetBrains Mono', monospace;
}

button {
  font-family: 'DM Sans', sans-serif;
}

a {
  color: var(--primary);
  text-decoration: none;
  
  &:hover {
    color: var(--primary-dark);
  }
}
```

**Step 5: Commit**
```bash
git add src/app/app.ts src/app/app.html src/app/app.scss src/styles.scss
git commit -m "feat: update app component with navigation and improved styling"
```

---

## Phase 2: Dashboard Feature

### Task 2.1: Create Dashboard Components

**Files:**
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/dashboard.component.ts`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/dashboard.component.html`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/dashboard.component.scss`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/stats-card/stats-card.component.ts`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/stats-card/stats-card.component.html`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/stats-card/stats-card.component.scss`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/recent-activity/recent-activity.component.ts`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/recent-activity/recent-activity.component.html`
- Create: `src/pdftranslator/frontend/src/app/features/dashboard/components/recent-activity/recent-activity.component.scss`

**Step 1: Create StatsCardComponent**
File: `src/app/features/dashboard/components/stats-card/stats-card.component.ts`
```typescript
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-stats-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './stats-card.component.html',
  styleUrl: './stats-card.component.scss'
})
export class StatsCardComponent {
  @Input() title = '';
  @Input() value: number = 0;
  @Input() icon = '';
  @Input() trend?: 'up' | 'down' | 'neutral';
  @Input() trendValue?: string;
}
```

File: `src/app/features/dashboard/components/stats-card/stats-card.component.html`
```html
<div class="stats-card">
  <div class="stats-card-icon">{{ icon }}</div>
  <div class="stats-card-content">
    <h3 class="stats-card-title">{{ title }}</h3>
    <p class="stats-card-value">{{ value }}</p>
    @if (trend) {
      <span class="stats-card-trend" [class]="'trend-' + trend">
        @if (trend === 'up') {
          ↑
        } @else if (trend === 'down') {
          ↓
        }
        {{ trendValue }}
      </span>
    }
  </div>
</div>
```

File: `src/app/features/dashboard/components/stats-card/stats-card.component.scss`
```scss
.stats-card {
  background-color: var(--surface);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .stats-card-icon {
    font-size: 2.5rem;
    line-height: 1;
  }

  .stats-card-content {
    flex: 1;

    .stats-card-title {
      font-size: 0.875rem;
      color: var(--text-secondary);
      margin-bottom: 0.25rem;
      font-weight: 500;
    }

    .stats-card-value {
      font-family: 'Outfit', sans-serif;
      font-size: 2rem;
      font-weight: 700;
      color: var(--text);
      margin: 0;
    }

    .stats-card-trend {
      font-size: 0.75rem;
      font-weight: 500;

      &.trend-up {
        color: var(--success);
      }

      &.trend-down {
        color: var(--error);
      }

      &.trend-neutral {
        color: var(--text-secondary);
      }
    }
  }
}
```

**Step 2: Create RecentActivityComponent**
File: `src/app/features/dashboard/components/recent-activity/recent-activity.component.ts`
```typescript
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RecentActivity } from '../../../../core/models';

@Component({
  selector: 'app-recent-activity',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './recent-activity.component.html',
  styleUrl: './recent-activity.component.scss'
})
export class RecentActivityComponent {
  @Input() activities: RecentActivity[] = [];

  getActivityIcon(type: string): string {
    const icons: Record<string, string> = {
      translation: '🌐',
      glossary: '📖',
      import: '📥',
      split: '✂️'
    };
    return icons[type] || '📝';
  }

  getActivityColor(type: string): string {
    const colors: Record<string, string> = {
      translation: 'var(--primary)',
      glossary: 'var(--success)',
      import: 'var(--info)',
      split: 'var(--accent)'
    };
    return colors[type] || 'var(--text-secondary)';
  }

  formatTime(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  }
}
```

File: `src/app/features/dashboard/components/recent-activity/recent-activity.component.html`
```html
<div class="recent-activity">
  <h3 class="section-title">Recent Activity</h3>
  <div class="activity-list">
    @for (activity of activities; track activity.id) {
      <div class="activity-item">
        <div class="activity-icon" [style.background-color]="getActivityColor(activity.type)">
          {{ getActivityIcon(activity.type) }}
        </div>
        <div class="activity-content">
          <p class="activity-action">{{ activity.action }}</p>
          @if (activity.work_title) {
            <p class="activity-work">{{ activity.work_title }}</p>
          }
        </div>
        <span class="activity-time">{{ formatTime(activity.timestamp) }}</span>
      </div>
    } @empty {
      <p class="empty-state">No recent activity</p>
    }
  </div>
</div>
```

File: `src/app/features/dashboard/components/recent-activity/recent-activity.component.scss`
```scss
.recent-activity {
  background-color: var(--surface);
  border-radius: 12px;
  padding: 1.5rem;

  .section-title {
    font-size: 1.125rem;
    margin-bottom: 1rem;
  }

  .activity-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;

    .activity-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem;
      border-radius: 8px;
      transition: background-color 0.2s;

      &:hover {
        background-color: var(--background);
      }

      .activity-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
      }

      .activity-content {
        flex: 1;

        .activity-action {
          font-size: 0.875rem;
          color: var(--text);
          margin: 0;
        }

        .activity-work {
          font-size: 0.75rem;
          color: var(--text-secondary);
          margin: 0;
        }
      }

      .activity-time {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .empty-state {
      text-align: center;
      color: var(--text-secondary);
      padding: 2rem;
    }
  }
}
```

**Step 3: Create DashboardComponent main**
File: `src/app/features/dashboard/dashboard.component.ts`
```typescript
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { WorkService } from '../../core/services/work.service';
import { GlossaryService } from '../../core/services/glossary.service';
import { DashboardStats, RecentActivity, Work, GlossaryTerm } from '../../core/models';
import { StatsCardComponent } from './components/stats-card/stats-card.component';
import { RecentActivityComponent } from './components/recent-activity/recent-activity.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, StatsCardComponent, RecentActivityComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private workService = inject(WorkService);
  private glossaryService = inject(GlossaryService);

  stats = {
    totalWorks: 0,
    totalGlossaryTerms: 0,
    translationsThisWeek: 0,
    averageProgress: 0
  };

  recentActivities: RecentActivity[] = [];
  isLoading = true;

  ngOnInit(): void {
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.isLoading = true;

    this.workService.getAll().subscribe({
      next: (works: Work[]) => {
        this.stats.totalWorks = works.length;
        const translatedCount = works.filter(w => w.translated_chapters > 0).length;
        const totalProgress = works.reduce((sum, w) => 
          sum + (w.total_chapters > 0 ? (w.translated_chapters / w.total_chapters) * 100 : 0), 0
        );
        this.stats.averageProgress = Math.round(totalProgress / works.length);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading works:', err);
        this.isLoading = false;
      }
    });

    this.glossaryService.getAll().subscribe({
      next: (terms: GlossaryTerm[]) => {
        this.stats.totalGlossaryTerms = terms.length;
      },
      error: (err) => console.error('Error loading glossary:', err)
    });

    this.dashboardService.getRecentActivities().subscribe({
      next: (activities: RecentActivity[]) => {
        this.recentActivities = activities;
      },
      error: (err) => console.error('Error loading activities:', err)
    });

    this.stats.translationsThisWeek = 5;
  }
}
```

File: `src/app/features/dashboard/dashboard.component.html`
```html
<div class="dashboard">
  <header class="dashboard-header">
    <h1>Dashboard</h1>
    <p class="subtitle">Welcome to PDFTranslator</p>
  </header>

  @if (isLoading) {
    <div class="loading">Loading dashboard data...</div>
  } @else {
    <div class="dashboard-content">
      <section class="stats-grid">
        <app-stats-card
          title="Total Works"
          [value]="stats.totalWorks"
          icon="📚"
          trend="up"
          trendValue="+3 this month">
        </app-stats-card>

        <app-stats-card
          title="Glossary Terms"
          [value]="stats.totalGlossaryTerms"
          icon="📖"
          trend="up"
          trendValue="+15 this week">
        </app-stats-card>

        <app-stats-card
          title="Translations This Week"
          [value]="stats.translationsThisWeek"
          icon="🌐"
          trend="neutral"
          trendValue="Same as last week">
        </app-stats-card>

        <app-stats-card
          title="Average Progress"
          [value]="stats.averageProgress"
          icon="📊"
          trend="up"
          trendValue="+5%">
        </app-stats-card>
      </section>

      <section class="activity-section">
        <app-recent-activity [activities]="recentActivities"></app-recent-activity>
      </section>
    </div>
  }
</div>
```

File: `src/app/features/dashboard/dashboard.component.scss`
```scss
.dashboard {
  .dashboard-header {
    margin-bottom: 2rem;

    h1 {
      margin-bottom: 0.25rem;
    }

    .subtitle {
      color: var(--text-secondary);
      margin: 0;
    }
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary);
  }

  .dashboard-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.5rem;
    }

    .activity-section {
      max-width: 600px;
    }
  }
}
```

**Step 4: Commit**
```bash
git add src/app/features/dashboard/
git commit -m "feat: add Dashboard feature with stats cards and recent activity"
```

---

*Note: Due to token limits, this plan covers Phase 1 (Core Setup) and Phase 2 (Dashboard). The remaining phases (Library, Translate, Glossary, Split Chapters) will follow the same TDD pattern with detailed implementation steps in subsequent plan documents or can be implemented iteratively.*
