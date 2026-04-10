# Document Workflow UI Design

**Date**: 2026-04-06  
**Branch**: feature/document-workflow-ui  
**Status**: Approved

## Executive Summary

Design and implement a React-based web UI for PDFTranslator that provides a visual interface for document processing workflows. The UI will allow users to upload PDF/EPUB/DOC/DOCX files, track task progress (split chapters, glossary, translation, audio generation), and interact with processed content.

## Architecture Overview

### Project Structure (Monorepo)

```
PDFTranslator/
├── frontend/                    # React application (NEW)
│   ├── src/
│   │   ├── components/
│   │   │   ├── containers/     # Logic-heavy components
│   │   │   └── ui/             # Presentational components (shadcn/ui)
│   │   ├── pages/              # Task screen pages
│   │   ├── stores/             # Zustand state stores
│   │   ├── services/           # API abstraction layer
│   │   ├── hooks/              # Custom React hooks
│   │   ├── types/              # TypeScript types
│   │   └── lib/                # Utilities
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts          # Vite for fast builds
│   └── tailwind.config.js
├── backend/                     # FastAPI application (NEW)
│   ├── api/
│   │   ├── routes/             # API endpoints
│   │   ├── models/             # Pydantic request/response models
│   │   └── services/           # Business logic wrapping existing tools
│   └── main.py
├── cli/                         # EXISTING: CLI (unchanged)
├── database/                    # EXISTING: Database layer (unchanged)
├── services/                    # EXISTING: Business logic (unchanged)
└── infrastructure/              # EXISTING: LLM integrations (unchanged)
```

### Technology Stack

**Frontend**:
- React 18 + TypeScript (strict mode)
- Vite (build tool)
- Zustand (state management)
- shadcn/ui (component library)
- Tailwind CSS
- React Router (routing)
- Axios (HTTP client)

**Backend**:
- FastAPI (async Python web framework)
- Pydantic (validation, already used in project)
- Existing tools from `cli/commands/` and `services/`

### Key Architectural Decisions

1. **Frontend/Backend Separation**: Frontend on port 5173, Backend on port 8000
2. **API-First Design**: FastAPI endpoints wrap existing logic without modifying stable code
3. **Type Safety**: Full TypeScript on frontend, Pydantic models on backend
4. **State Management**: Zustand for file uploads, task progress, and UI state
5. **Mock Data Support**: API layer can return mock data when backend not available

## Component Architecture

### Container Components (Logic)

**`FileUploadContainer.tsx`**
- Drag & drop zone
- File type validation (.pdf, .epub, .doc, .docx)
- Calls `api.files.upload(files)`
- Error handling for invalid files

**`FileListContainer.tsx`**
- Displays uploaded files as cards
- Shows task status badges per file
- File selection logic
- Trigger/retry task actions

**`TaskDetailContainer.tsx`**
- Tab navigation for task views
- Loads task-specific data
- Handles task-specific actions

### Presentational Components (UI)

**`file-drop-zone.tsx`**
- Drag active/leave states
- Visual feedback
- File input fallback

**`file-card.tsx`**
- File name, size, type icon
- Task status badges (4 tasks)
- Click to select
- Last updated timestamp

**`task-badge.tsx`**
- Status colors: pending (gray), in-progress (blue), completed (green), failed (red)
- Progress percentage for in-progress
- Timestamp tooltip
- Retry button on failed

**`audio-player.tsx`**
- HTML5 audio element
- Play/pause, seek, volume
- Progress bar
- Download buttons (M4A, MP3)

**`parallel-text-viewer.tsx`**
- Side-by-side layout
- Synchronized scrolling
- Inline edit mode
- Language selector

### Pages

**`Dashboard.tsx`**
- File upload zone (top)
- File list (below)
- Selected file detail panel (right sidebar)

**`SplitChaptersScreen.tsx`**
- Chapter list with page ranges
- Preview button per chapter
- Edit title inline
- Merge with previous/next
- Run auto-detection again

**`GlossaryScreen.tsx`**
- Search input
- Filter dropdown (by type/context)
- Term cards: source → target
- Context snippet
- Edit/delete actions
- Add term button
- Export CSV / Import terms

**`TranslatedScreen.tsx`**
- Language selector (source/target)
- Parallel text viewer
- Edit translation mode
- Save draft / regenerate buttons

**`AudioScreen.tsx`**
- Chapter list with audio players
- Generate all button
- Download individual or all as ZIP

## State Management (Zustand)

### FileStore

```typescript
interface FileStore {
  files: FileItem[];
  selectedFileId: string | null;
  addFiles: (files: File[]) => Promise<void>;
  removeFile: (id: string) => void;
  selectFile: (id: string) => void;
}

interface FileItem {
  id: string;
  name: string;
  size: number;
  type: 'pdf' | 'epub' | 'doc' | 'docx';
  uploadedAt: Date;
  workId?: number;
  volumeId?: number;
}
```

### TaskStore

```typescript
interface TaskStore {
  tasks: Record<string, TaskStatus>;  // fileId -> task status
  updateTaskStatus: (fileId: string, task: TaskType, status: TaskStatusEnum) => void;
  retryTask: (fileId: string, task: TaskType) => Promise<void>;
}

type TaskType = 'splitChapters' | 'glossary' | 'translated' | 'audioGenerated';

interface TaskStatus {
  splitChapters: TaskState;
  glossary: TaskState;
  translated: TaskState;
  audioGenerated: TaskState;
}

interface TaskState {
  status: 'pending' | 'in-progress' | 'completed' | 'failed';
  updatedAt: Date;
  error?: string;
  progress?: number;  // 0-100
}
```

## API Design

### Endpoints

**Files**
- `POST /api/files/upload` - Upload files
- `GET /api/files` - List all files
- `GET /api/files/{id}` - Get file details
- `DELETE /api/files/{id}` - Delete file

**Tasks**
- `POST /api/tasks/{fileId}/start` - Start a task
- `GET /api/tasks/{fileId}/status` - Get task status
- `POST /api/tasks/{fileId}/retry` - Retry failed task

**Chapters**
- `GET /api/chapters/{fileId}` - List chapters
- `PUT /api/chapters/{chapterId}` - Update chapter (title, merge)
- `POST /api/chapters/{fileId}/detect` - Re-run auto-detection

**Glossary**
- `GET /api/glossary/{fileId}` - List glossary entries
- `GET /api/glossary/{fileId}/search?q=query` - Search entries
- `POST /api/glossary/{fileId}` - Add entry
- `PUT /api/glossary/{entryId}` - Update entry
- `DELETE /api/glossary/{entryId}` - Delete entry

**Translation**
- `GET /api/translation/{fileId}` - Get translation data
- `PUT /api/translation/{chunkId}` - Update translated text

**Audio**
- `POST /api/audio/{fileId}/generate` - Generate audio
- `GET /api/audio/{fileId}/status` - Get generation status
- `GET /api/audio/{fileId}/download` - Download audio file

## UI/UX Design

### Aesthetic Direction: Refined Minimalism with Editorial Typography

**Typography**:
- Display: JetBrains Mono (chapter markers, code)
- UI: Inter (pragmatic for document workflow)

**Color Palette**:
- Background: #FFFFFF
- Foreground: #0A0A0A
- Accent: #0066FF (active states)
- Success: #10B981
- Warning: #F59E0B
- Error: #EF4444
- Muted: #6B7280

**Layout Principles**:
- Desktop-first with responsive breakpoints
- Generous whitespace
- Clear visual hierarchy
- Minimal clicks to trigger actions

**Motion**:
- Fade-in on file cards (200ms)
- Progress bar animations
- Micro-interactions on task triggers
- Synchronized scrolling in parallel text view

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│ PDFTranslator [Document Workflow]                           │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Drop PDF, EPUB, DOC, or DOCX files here            │     │
│ │ or click to browse                                  │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                             │
│ Files (3)                                                   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 📄 book.pdf                                            │   │
│ │ ├─ Chapters: [✓ completed] 12 chapters                │   │
│ │ ├─ Glossary: [⏳ in-progress] 45 terms                │   │
│ │ ├─ Translated: [pending]                              │   │
│ │ └─ Audio: [pending]                                   │   │
│ └───────────────────────────────────────────────────────┘   │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling

### Frontend
- File validation before upload (extension, size)
- Toast notifications for errors
- Retry buttons on failed tasks
- Graceful degradation if backend unavailable

### Backend
- Pydantic validation on all inputs
- Proper HTTP status codes
- Error messages in response body
- Logging for debugging

## Testing Strategy

**Frontend**:
- Vitest for unit tests
- React Testing Library for component tests
- Mock API responses for integration tests

**Backend**:
- pytest (already used in project)
- Test endpoints with mock file processing
- Test error cases

## Security Considerations

- CORS configuration for frontend/backend separation
- File size limits (max 100MB per file)
- File type validation (whitelist: .pdf, .epub, .doc, .docx)
- Input sanitization on all user inputs
- No direct file system access from frontend

## Deployment Considerations

- Frontend: Build with Vite, serve static files from FastAPI or CDN
- Backend: Run with uvicorn, can be containerized
- Database: Use existing PostgreSQL setup
- Environment variables for configuration

## Implementation Phases

### Phase 1: Project Setup (Infrastructure)
- Initialize frontend with Vite + React + TypeScript
- Install shadcn/ui, Zustand, Tailwind
- Initialize backend with FastAPI
- Set up project structure

### Phase 2: Backend API (Core)
- Create FastAPI routes
- Implement file upload endpoint
- Create task status endpoints
- Wrap existing CLI tools in API services

### Phase 3: Frontend Core (Dashboard)
- Create Zustand stores
- Implement file upload component
- Build file list with task badges
- Dashboard page layout

### Phase 4: Task Screens
- Split Chapters screen
- Glossary screen with search/filter
- Translated screen with parallel view
- Audio screen with player

### Phase 5: Polish & Testing
- Add animations and micro-interactions
- Error handling and edge cases
- Unit and integration tests
- Documentation

## Success Criteria

1. ✅ Users can upload PDF/EPUB/DOC/DOCX files via drag & drop
2. ✅ File list displays all uploaded files with task status
3. ✅ Each task shows pending/in-progress/completed/failed status
4. ✅ Users can trigger/retry tasks from dashboard
5. ✅ Split Chapters screen allows preview and manual adjustments
6. ✅ Glossary screen allows search, edit, and filter
7. ✅ Translated screen shows side-by-side view with editing
8. ✅ Audio screen has player, download, and regenerate options
9. ✅ All changes are in feature branch, no modification to stable code
10. ✅ TypeScript strict mode, proper error handling, responsive design

## Constraints

- No modification to existing stable code (cli/, database/, services/, infrastructure/)
- All changes must live in feature/document-workflow-ui branch
- Maintain high code readability and maintainability
- Avoid over-engineering; prioritize clarity and extensibility
- Follow existing Python code style (88 char line length, double quotes)
