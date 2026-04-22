# Frontend Mock Data Integration Design

**Date:** 2026-04-10  
**Branch:** feature/frontend-mock-data  
**Status:** Design Approved

## Overview

Replace current basic frontend with a feature-rich Angular 17+ application that mirrors CLI functionality. Uses Angular InMemoryWebAPI for mock data during development, enabling full CRUD operations simulation before backend integration.

## Architecture

### Feature-Based Module Structure

```
src/app/
├── core/
│   ├── interceptors/
│   │   └── api.interceptor.ts
│   ├── services/
│   │   ├── api.service.ts
│   │   ├── theme.service.ts
│   │   └── mock.service.ts
│   ├── models/
│   │   ├── work.model.ts
│   │   ├── volume.model.ts
│   │   ├── chapter.model.ts
│   │   ├── glossary-term.model.ts
│   │   └── translation-progress.model.ts
│   └── mock/
│       ├── in-memory-data.service.ts
│       └── mock-data.ts
├── features/
│   ├── dashboard/
│   │   ├── components/
│   │   │   ├── stats-card/
│   │   │   ├── recent-activity/
│   │   │   └── translation-chart/
│   │   ├── services/
│   │   │   └── dashboard.service.ts
│   │   └── dashboard.routes.ts
│   ├── library/
│   │   ├── components/
│   │   │   ├── work-list/
│   │   │   ├── work-detail/
│   │   │   ├── volume-viewer/
│   │   │   └── chapter-list/
│   │   ├── services/
│   │   │   └── library.service.ts
│   │   └── library.routes.ts
│   ├── translate/
│   │   ├── components/
│   │   │   ├── work-selector/
│   │   │   ├── scope-selector/
│   │   │   ├── progress-tracker/
│   │   │   └── translation-viewer/
│   │   ├── services/
│   │   │   └── translate.service.ts
│   │   └── translate.routes.ts
│   ├── glossary/
│   │   ├── components/
│   │   │   ├── term-list/
│   │   │   ├── term-editor/
│   │   │   └── entity-chart/
│   │   ├── services/
│   │   │   └── glossary.service.ts
│   │   └── glossary.routes.ts
│   └── split-chapters/
│       ├── components/
│       │   ├── volume-selector/
│       │   ├── text-editor/
│       │   └── chapter-parser/
│       ├── services/
│       │   └── split.service.ts
│       └── split.routes.ts
└── shared/
    ├── components/
    │   ├── work-card/
    │   ├── volume-tree/
    │   ├── chapter-item/
    │   ├── progress-bar/
    │   ├── language-selector/
    │   ├── provider-selector/
    │   ├── status-badge/
    │   └── empty-state/
    └── services/
        └── notification.service.ts
```

## Mock Data Strategy

### Angular InMemoryWebAPI

**Implementation:**
- `InMemoryDataService` implements `InMemoryDbService`
- Creates realistic mock data matching CLI entities
- Supports HTTP methods: GET, POST, PUT, DELETE
- Intercepts HttpClient requests automatically

**Mock Entities:**

```typescript
// Works (Books)
interface Work {
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

// Volumes
interface Volume {
  id: number;
  work_id: number;
  volume_number: number;
  chapters: Chapter[];
  full_text?: string;
  translated_text?: string;
  created_at: Date;
}

// Chapters
interface Chapter {
  id: number;
  volume_id: number;
  chapter_number: number;
  title: string;
  chapter_type: 'prologue' | 'chapter' | 'epilogue';
  original_text?: string;
  translated_text?: string;
  is_translated: boolean;
  start_position?: number;
  end_position?: number;
  created_at: Date;
  updated_at: Date;
}

// Glossary Terms
interface GlossaryTerm {
  id: number;
  work_id: number;
  term: string;
  translation?: string;
  entity_type: 'character' | 'place' | 'skill' | 'item' | 'spell' | 'faction' | 'title' | 'race' | 'other';
  context?: string;
  is_proper_noun: boolean;
  frequency: number;
  source_lang: string;
  target_lang: string;
  created_at: Date;
  updated_at: Date;
}

// Translation Progress
interface TranslationProgress {
  id: string;
  work_id: number;
  scope: 'all_book' | 'all_volume' | 'single_chapter';
  volume_id?: number;
  chapter_id?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  total_chunks: number;
  completed_chunks: number;
  current_chunk?: string;
  started_at?: Date;
  completed_at?: Date;
  error?: string;
}
```

## Features Specification

### 1. Dashboard

**Route:** `/dashboard` (default route)

**Components:**
- `StatsCardComponent` - Displays key metrics
  - Total works in library
  - Total glossary terms
  - Translations completed this week
  - Average translation progress

- `RecentActivityComponent` - Shows last 10 actions
  - Translation started/completed
  - Glossary term added
  - Work imported
  - Chapter split

- `TranslationChartComponent` - Visual translation status
  - Pie chart: Completed vs In Progress vs Pending
  - By work breakdown

**Data Required:**
```typescript
interface DashboardStats {
  total_works: number;
  total_glossary_terms: number;
  translations_this_week: number;
  average_progress: number;
}

interface RecentActivity {
  id: string;
  type: 'translation' | 'glossary' | 'import' | 'split';
  action: string;
  work_title?: string;
  timestamp: Date;
}
```

### 2. Library (add-to-database)

**Route:** `/library`

**Components:**
- `WorkListComponent` - Grid/list view of all works
  - Search by title/author
  - Filter by translation status
  - Sort by date, title, progress

- `WorkDetailComponent` - Single work view
  - Work metadata (title, author, dates)
  - Volumes list with chapter counts
  - Translation progress per volume
  - Actions: Translate, Build Glossary, Split Chapters

- `VolumeViewerComponent` - Volume detail view
  - Volume chapters list
  - Full text viewer (if available)
  - Translation status per chapter

- `ChapterListComponent` - Chapter listing with actions
  - Chapter title and type badge
  - Translation status indicator
  - Actions: View, Translate, Edit

**User Flow:**
1. Browse works in grid/list
2. Click work → View details
3. Click volume → View chapters
4. Click chapter → View/edit content

### 3. Translate

**Route:** `/translate`

**Components:**
- `WorkSelectorComponent` - Select work to translate
  - Work cards with structure preview
  - Shows translation status (green/yellow/red)
  - Displays volume/chapter counts

- `ScopeSelectorComponent` - Select translation scope
  - Radio buttons: All Book, All Volume, Single Chapter
  - Dynamic volume/chapter selection based on scope
  - Shows estimated chunks count

- `ProgressTrackerComponent` - Real-time progress display
  - Progress bar with percentage
  - Current chunk being translated
  - Speed (chunks/minute)
  - Estimated time remaining
  - Pause/Resume/Cancel buttons

- `TranslationViewerComponent` - Side-by-side view
  - Original text (left)
  - Translated text (right)
  - Highlight glossary terms
  - Export options

**User Flow:**
1. Select work from library
2. Choose scope (all book/volume/chapter)
3. Configure languages and provider
4. Start translation
5. Monitor progress in real-time
6. Review and export

### 4. Glossary

**Route:** `/glossary`

**Components:**
- `TermListComponent` - Glossary terms table
  - Columns: Term, Translation, Type, Frequency, Context
  - Search and filter by entity type
  - Sort by frequency, alphabetical
  - Pagination

- `TermEditorComponent` - Add/Edit term modal
  - Term input
  - Translation input
  - Entity type dropdown
  - Context textarea
  - Proper noun checkbox
  - Save/Cancel buttons

- `EntityChartComponent` - Entity distribution chart
  - Donut chart by entity type
  - Click segment to filter list

**User Flow:**
1. View all glossary terms
2. Search/filter terms
3. Click term to edit
4. Add new term
5. View entity distribution

### 5. Split Chapters

**Route:** `/split`

**Components:**
- `VolumeSelectorComponent` - Select volume to split
  - Work selector first
  - Volume dropdown with chapter count
  - Shows if already has chapters

- `TextEditorComponent` - Full text editor
  - Large textarea with volume text
  - Block format instructions sidebar
  - Visual block markers
  - Save/Parse buttons

- `ChapterParserComponent` - Parsed chapters preview
  - List of detected blocks
  - Block type badges (Prologue/Chapter/Epilogue)
  - Edit individual block
  - Confirm/Cancel actions

**Block Format:**
```
[===Type="Prologue"===]
... prologue text ...

[===End Block===]

[===Type="Chapter"===]
... chapter text ...

[===End Block===]
```

**User Flow:**
1. Select work and volume
2. View/edit full text
3. Add block markers
4. Parse and preview chapters
5. Confirm to save chapters

## Shared Components

### Status Indicators

**StatusBadgeComponent:**
- Inputs: `status` ('success' | 'warning' | 'error' | 'info')
- Inputs: `text` (string)
- Styles: Color-coded badges with icons

**ProgressBarComponent:**
- Inputs: `progress` (0-100)
- Inputs: `color` ('primary' | 'accent' | 'warn')
- Inputs: `mode` ('determinate' | 'indeterminate')
- Features: Animated fill, percentage text

### Selection Components

**LanguageSelectorComponent:**
- Uses BCP47Language enum from backend
- Search autocomplete
- Flag icons (optional)

**ProviderSelectorComponent:**
- LLMProvider enum
- Radio cards with icons
- Provider descriptions

### Data Display

**WorkCardComponent:**
- Work title and author
- Volume/chapter counts
- Translation progress bar
- Status badge
- Click to navigate

**VolumeTreeComponent:**
- Expandable tree structure
- Volume nodes with chapter children
- Status icons per chapter
- Selection events

**ChapterItemComponent:**
- Chapter title and type badge
- Translation status
- Actions menu
- Click to view

### UI Utilities

**EmptyStateComponent:**
- Illustration
- Message text
- Optional action button
- Used in lists with no data

## Data Flow

### Mock Data Flow (Development)

```
Component → Service → HttpClient → InMemoryWebAPI → Mock Data
                                                     ↓
Component ← Service ← HttpClient ← InMemoryWebAPI ←
```

### Real API Flow (Production)

```
Component → Service → HttpClient → API Interceptor → Backend API
                                                         ↓
Component ← Service ← HttpClient ← API Interceptor ←
```

### Switching Between Mock and Real

**Environment Configuration:**
```typescript
// environment.ts (development)
export const environment = {
  production: false,
  useMockData: true
};

// environment.prod.ts (production)
export const environment = {
  production: true,
  useMockData: false
};
```

**App Configuration:**
```typescript
// app.config.ts
if (environment.useMockData) {
  providers.push(
    InMemoryWebApiModule.forRoot(InMemoryDataService, { delay: 500 })
  );
}
```

## Routing Structure

```typescript
const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component')
      .then(m => m.DashboardComponent)
  },
  {
    path: 'library',
    loadChildren: () => import('./features/library/library.routes')
      .then(m => m.libraryRoutes)
  },
  {
    path: 'translate',
    loadChildren: () => import('./features/translate/translate.routes')
      .then(m => m.translateRoutes)
  },
  {
    path: 'glossary',
    loadChildren: () => import('./features/glossary/glossary.routes')
      .then(m => m.glossaryRoutes)
  },
  {
    path: 'split',
    loadChildren: () => import('./features/split-chapters/split.routes')
      .then(m => m.splitRoutes)
  }
];
```

## Styling Guidelines

### Color Palette (CSS Custom Properties)

```scss
:root {
  // Primary colors
  --primary: #6366f1;
  --primary-light: #818cf8;
  --primary-dark: #4f46e5;
  
  // Accent colors
  --accent: #f59e0b;
  --accent-light: #fbbf24;
  
  // Status colors
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
  
  // Neutral colors
  --background: #f8fafc;
  --surface: #ffffff;
  --text: #1e293b;
  --text-secondary: #64748b;
  --border: #e2e8f0;
  
  // Dark theme
  --dark-background: #0f172a;
  --dark-surface: #1e293b;
  --dark-text: #f1f5f9;
}

[data-theme="dark"] {
  --background: var(--dark-background);
  --surface: var(--dark-surface);
  --text: var(--dark-text);
}
```

### Typography

```scss
// Headings
h1, h2, h3, h4, h5, h6 {
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
}

// Body
body {
  font-family: 'DM Sans', sans-serif;
  font-weight: 400;
  line-height: 1.6;
}

// Code/Pre
code, pre {
  font-family: 'JetBrains Mono', monospace;
}
```

## Implementation Phases

### Phase 1: Core Setup (Current)
1. Create branch `feature/frontend-mock-data`
2. Install InMemoryWebAPI package
3. Create mock data service
4. Set up routing structure
5. Create shared components

### Phase 2: Dashboard
1. Stats card component
2. Recent activity component
3. Translation chart component
4. Dashboard service with mock data

### Phase 3: Library
1. Work list component
2. Work detail component
3. Volume viewer component
4. Chapter list component
5. Library service with mock data

### Phase 4: Glossary
1. Term list component
2. Term editor component
3. Entity chart component
4. Glossary service with mock data

### Phase 5: Translate
1. Work selector component
2. Scope selector component
3. Progress tracker component
4. Translation viewer component
5. Translate service with mock data

### Phase 6: Split Chapters
1. Volume selector component
2. Text editor component
3. Chapter parser component
4. Split service with mock data

## Testing Strategy

### Unit Tests
- Component tests with Jest
- Service tests with HttpClientTestingModule
- Mock data validation tests

### Integration Tests
- Feature module tests
- Routing tests
- Mock API interaction tests

### E2E Tests
- User flows with Cypress/Playwright
- Mock data scenarios

## Success Criteria

- ✅ All 5 features implemented
- ✅ InMemoryWebAPI working with realistic data
- ✅ Routing and navigation functional
- ✅ Shared components reusable
- ✅ Dark/light theme support
- ✅ Responsive design
- ✅ No console errors
- ✅ Build successful
- ✅ Documentation updated

## Dependencies

```json
{
  "dependencies": {
    "angular-in-memory-web-api": "^0.17.0",
    "@angular/material": "^17.0.0",
    "chart.js": "^4.4.0",
    "ng2-charts": "^5.0.0"
  }
}
```

## Next Steps

1. Invoke `writing-plans` skill to create detailed implementation plan
2. Implement Phase 1: Core Setup
3. Progress through remaining phases
4. Update CHANGELOG.md after each phase
5. Create PR when all features complete
