# Document Workflow UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a React web UI for document processing workflow with file upload, task tracking, and task-specific screens

**Architecture:** Monorepo with frontend/ (React + Vite + Zustand + shadcn/ui) and backend/ (FastAPI wrapping existing CLI tools). All changes in feature branch, no modification to stable code.

**Tech Stack:** React 18, TypeScript (strict), Vite, Zustand, shadcn/ui, Tailwind CSS, FastAPI, Pydantic

---

## Phase 1: Project Setup (Infrastructure)

### Task 1.1: Initialize Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.gitignore`

**Step 1: Create frontend directory and initialize Vite project**

Run:
```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator
npm create vite@latest frontend -- --template react-ts
```

Expected: Creates frontend/ directory with React + TypeScript + Vite setup

**Step 2: Verify project structure**

Run:
```bash
ls -la frontend/
```

Expected: See `package.json`, `tsconfig.json`, `vite.config.ts`, `src/`, `public/`

**Step 3: Install dependencies**

Run:
```bash
cd frontend && npm install
```

Expected: Installs React, TypeScript, Vite dependencies successfully

**Step 4: Test dev server**

Run:
```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts on port 5173, shows default Vite + React page

**Step 5: Stop dev server and commit**

Run:
```bash
git add frontend/
git commit -m "feat: initialize frontend with Vite + React + TypeScript"
```

---

### Task 1.2: Install UI Dependencies

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/index.css`

**Step 1: Install Tailwind CSS**

Run:
```bash
cd frontend && npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Expected: Creates `tailwind.config.js` and `postcss.config.js`

**Step 2: Install Zustand**

Run:
```bash
cd frontend && npm install zustand
```

Expected: Installs Zustand state management library

**Step 3: Install React Router**

Run:
```bash
cd frontend && npm install react-router-dom
```

Expected: Installs React Router for navigation

**Step 4: Install Axios**

Run:
```bash
cd frontend && npm install axios
```

Expected: Installs Axios HTTP client

**Step 5: Configure Tailwind**

Edit `frontend/tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Edit `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 6: Test Tailwind**

Run:
```bash
cd frontend && npm run dev
```

Expected: Dev server starts without errors

**Step 7: Commit dependencies**

Run:
```bash
git add frontend/
git commit -m "feat: install Tailwind, Zustand, React Router, Axios"
```

---

### Task 1.3: Setup shadcn/ui

**Files:**
- Modify: `frontend/tsconfig.json`
- Create: `frontend/components.json`
- Create: `frontend/src/lib/utils.ts`

**Step 1: Initialize shadcn/ui**

Run:
```bash
cd frontend && npx shadcn-ui@latest init
```

When prompted:
- Style: Default
- Base color: Neutral
- CSS variables: Yes

Expected: Creates `components.json` and `src/lib/utils.ts`

**Step 2: Verify shadcn/ui setup**

Run:
```bash
ls -la frontend/src/lib/
```

Expected: See `utils.ts` file

**Step 3: Install first shadcn/ui component (Button)**

Run:
```bash
cd frontend && npx shadcn-ui@latest add button
```

Expected: Creates `frontend/src/components/ui/button.tsx`

**Step 4: Verify component installation**

Run:
```bash
ls -la frontend/src/components/ui/
```

Expected: See `button.tsx` file

**Step 5: Commit shadcn/ui setup**

Run:
```bash
git add frontend/
git commit -m "feat: setup shadcn/ui and install Button component"
```

---

### Task 1.4: Create Project Directory Structure

**Files:**
- Create: `frontend/src/components/containers/.gitkeep`
- Create: `frontend/src/components/ui/.gitkeep` (already exists)
- Create: `frontend/src/pages/.gitkeep`
- Create: `frontend/src/stores/.gitkeep`
- Create: `frontend/src/services/.gitkeep`
- Create: `frontend/src/hooks/.gitkeep`
- Create: `frontend/src/types/.gitkeep`

**Step 1: Create directory structure**

Run:
```bash
cd frontend/src
mkdir -p components/containers
mkdir -p pages
mkdir -p stores
mkdir -p services
mkdir -p hooks
mkdir -p types
touch components/containers/.gitkeep
touch pages/.gitkeep
touch stores/.gitkeep
touch services/.gitkeep
touch hooks/.gitkeep
touch types/.gitkeep
```

Expected: Creates all directories with .gitkeep files

**Step 2: Verify structure**

Run:
```bash
tree -L 3 frontend/src/
```

Expected: See organized directory structure

**Step 3: Commit structure**

Run:
```bash
git add frontend/src/
git commit -m "feat: create frontend directory structure"
```

---

## Phase 2: TypeScript Types & API Abstraction

### Task 2.1: Create TypeScript Types

**Files:**
- Create: `frontend/src/types/file.ts`
- Create: `frontend/src/types/task.ts`
- Create: `frontend/src/types/chapter.ts`
- Create: `frontend/src/types/glossary.ts`
- Create: `frontend/src/types/translation.ts`
- Create: `frontend/src/types/audio.ts`
- Create: `frontend/src/types/index.ts`

**Step 1: Create file types**

Create `frontend/src/types/file.ts`:
```typescript
export type FileType = 'pdf' | 'epub' | 'doc' | 'docx';

export interface FileItem {
  id: string;
  name: string;
  size: number;
  type: FileType;
  uploadedAt: Date;
  workId?: number;
  volumeId?: number;
}

export interface FileUploadResponse {
  id: string;
  name: string;
  size: number;
  type: FileType;
  uploadedAt: string;
  workId: number;
  volumeId: number;
}
```

**Step 2: Create task types**

Create `frontend/src/types/task.ts`:
```typescript
export type TaskType = 'splitChapters' | 'glossary' | 'translated' | 'audioGenerated';

export type TaskStatusEnum = 'pending' | 'in-progress' | 'completed' | 'failed';

export interface TaskState {
  status: TaskStatusEnum;
  updatedAt: Date;
  error?: string;
  progress?: number;
}

export interface TaskStatus {
  splitChapters: TaskState;
  glossary: TaskState;
  translated: TaskState;
  audioGenerated: TaskState;
}

export interface TaskStartRequest {
  fileId: string;
  taskType: TaskType;
}

export interface TaskStartResponse {
  taskId: string;
  status: TaskStatusEnum;
  message: string;
}
```

**Step 3: Create chapter types**

Create `frontend/src/types/chapter.ts`:
```typescript
export interface Chapter {
  id: number;
  volumeId: number;
  chapterNumber: number;
  title: string;
  startPage?: number;
  endPage?: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface ChapterUpdate {
  title?: string;
  mergeWithPrevious?: boolean;
}
```

**Step 4: Create glossary types**

Create `frontend/src/types/glossary.ts`:
```typescript
export interface GlossaryEntry {
  id: number;
  workId: number;
  volumeId?: number;
  sourceTerm: string;
  targetTerm: string;
  context?: string;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface GlossaryCreate {
  sourceTerm: string;
  targetTerm: string;
  context?: string;
  notes?: string;
}

export interface GlossaryUpdate {
  targetTerm?: string;
  context?: string;
  notes?: string;
}
```

**Step 5: Create translation types**

Create `frontend/src/types/translation.ts`:
```typescript
export interface TranslationChunk {
  id: number;
  chapterId: number;
  originalText: string;
  translatedText: string;
  order: number;
}

export interface TranslationData {
  fileId: string;
  chapters: TranslationChapter[];
}

export interface TranslationChapter {
  chapterId: number;
  chapterTitle: string;
  chunks: TranslationChunk[];
}

export interface TranslationUpdate {
  chunkId: number;
  translatedText: string;
}
```

**Step 6: Create audio types**

Create `frontend/src/types/audio.ts`:
```typescript
export type AudioFormat = 'm4a' | 'mp3' | 'wav' | 'aiff';

export interface AudioFile {
  chapterId: number;
  chapterTitle: string;
  format: AudioFormat;
  duration: number;
  url: string;
  size: number;
}

export interface AudioStatus {
  status: 'pending' | 'generating' | 'completed' | 'failed';
  progress: number;
  audioFiles?: AudioFile[];
  error?: string;
}

export interface AudioGenerateRequest {
  fileId: string;
  format?: AudioFormat;
  voice?: string;
}
```

**Step 7: Create index export**

Create `frontend/src/types/index.ts`:
```typescript
export * from './file';
export * from './task';
export * from './chapter';
export * from './glossary';
export * from './translation';
export * from './audio';
```

**Step 8: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 9: Commit types**

Run:
```bash
git add frontend/src/types/
git commit -m "feat: create TypeScript type definitions"
```

---

### Task 2.2: Create API Service Layer

**Files:**
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/mockData.ts`
- Create: `frontend/src/services/config.ts`

**Step 1: Create API config**

Create `frontend/src/services/config.ts`:
```typescript
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const config = {
  useMockData: USE_MOCK_DATA,
  apiBaseUrl: API_BASE_URL,
};
```

**Step 2: Create mock data**

Create `frontend/src/services/mockData.ts`:
```typescript
import type { FileItem, TaskStatus } from '../types';

export const mockFiles: FileItem[] = [
  {
    id: '1',
    name: 'book.pdf',
    size: 2048576,
    type: 'pdf',
    uploadedAt: new Date('2026-04-06T10:00:00Z'),
    workId: 1,
    volumeId: 1,
  },
  {
    id: '2',
    name: 'novel.epub',
    size: 1536000,
    type: 'epub',
    uploadedAt: new Date('2026-04-06T11:00:00Z'),
    workId: 2,
    volumeId: 2,
  },
];

export const mockTaskStatus: Record<string, TaskStatus> = {
  '1': {
    splitChapters: { status: 'completed', updatedAt: new Date('2026-04-06T10:30:00Z') },
    glossary: { status: 'in-progress', updatedAt: new Date('2026-04-06T11:00:00Z'), progress: 65 },
    translated: { status: 'pending', updatedAt: new Date('2026-04-06T10:00:00Z') },
    audioGenerated: { status: 'pending', updatedAt: new Date('2026-04-06T10:00:00Z') },
  },
  '2': {
    splitChapters: { status: 'completed', updatedAt: new Date('2026-04-06T11:30:00Z') },
    glossary: { status: 'completed', updatedAt: new Date('2026-04-06T12:00:00Z') },
    translated: { status: 'completed', updatedAt: new Date('2026-04-06T12:30:00Z') },
    audioGenerated: { status: 'failed', updatedAt: new Date('2026-04-06T13:00:00Z'), error: 'Voice not available' },
  },
};
```

**Step 3: Create API service**

Create `frontend/src/services/api.ts`:
```typescript
import axios from 'axios';
import { config } from './config';
import { mockFiles, mockTaskStatus } from './mockData';
import type {
  FileItem,
  FileUploadResponse,
  TaskStatus,
  TaskStartResponse,
  Chapter,
  GlossaryEntry,
  TranslationData,
  AudioStatus,
} from '../types';

const api = axios.create({
  baseURL: config.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fileApi = {
  upload: async (files: File[]): Promise<FileUploadResponse[]> => {
    if (config.useMockData) {
      return files.map((file, index) => ({
        id: `${Date.now() + index}`,
        name: file.name,
        size: file.size,
        type: file.name.split('.').pop() as 'pdf' | 'epub' | 'doc' | 'docx',
        uploadedAt: new Date().toISOString(),
        workId: Date.now() + index,
        volumeId: Date.now() + index,
      }));
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    const response = await api.post<FileUploadResponse[]>('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  list: async (): Promise<FileItem[]> => {
    if (config.useMockData) {
      return mockFiles;
    }

    const response = await api.get<FileItem[]>('/files');
    return response.data;
  },

  get: async (id: string): Promise<FileItem> => {
    if (config.useMockData) {
      const file = mockFiles.find((f) => f.id === id);
      if (!file) throw new Error('File not found');
      return file;
    }

    const response = await api.get<FileItem>(`/files/${id}`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    if (config.useMockData) {
      return;
    }

    await api.delete(`/files/${id}`);
  },
};

export const taskApi = {
  start: async (fileId: string, taskType: string): Promise<TaskStartResponse> => {
    if (config.useMockData) {
      return {
        taskId: `${fileId}-${taskType}`,
        status: 'in-progress',
        message: `Task ${taskType} started`,
      };
    }

    const response = await api.post<TaskStartResponse>(`/tasks/${fileId}/start`, { taskType });
    return response.data;
  },

  getStatus: async (fileId: string): Promise<TaskStatus> => {
    if (config.useMockData) {
      const status = mockTaskStatus[fileId];
      if (!status) throw new Error('Task status not found');
      return status;
    }

    const response = await api.get<TaskStatus>(`/tasks/${fileId}/status`);
    return response.data;
  },

  retry: async (fileId: string, taskType: string): Promise<TaskStartResponse> => {
    if (config.useMockData) {
      return {
        taskId: `${fileId}-${taskType}-retry`,
        status: 'in-progress',
        message: `Task ${taskType} retry started`,
      };
    }

    const response = await api.post<TaskStartResponse>(`/tasks/${fileId}/retry`, { taskType });
    return response.data;
  },
};

export const chapterApi = {
  list: async (fileId: string): Promise<Chapter[]> => {
    if (config.useMockData) {
      return [
        { id: 1, volumeId: 1, chapterNumber: 1, title: 'Chapter 1: The Beginning', createdAt: new Date(), updatedAt: new Date() },
        { id: 2, volumeId: 1, chapterNumber: 2, title: 'Chapter 2: The Journey', createdAt: new Date(), updatedAt: new Date() },
      ];
    }

    const response = await api.get<Chapter[]>(`/chapters/${fileId}`);
    return response.data;
  },

  update: async (chapterId: number, data: { title?: string }): Promise<Chapter> => {
    if (config.useMockData) {
      return {
        id: chapterId,
        volumeId: 1,
        chapterNumber: 1,
        title: data.title || 'Updated Chapter',
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    }

    const response = await api.put<Chapter>(`/chapters/${chapterId}`, data);
    return response.data;
  },
};

export const glossaryApi = {
  list: async (fileId: string): Promise<GlossaryEntry[]> => {
    if (config.useMockData) {
      return [
        { id: 1, workId: 1, sourceTerm: 'arcane', targetTerm: 'arcano', context: 'The arcane symbols glowed...', createdAt: new Date(), updatedAt: new Date() },
        { id: 2, workId: 1, sourceTerm: 'kingdom', targetTerm: 'reino', context: 'The kingdom flourished...', createdAt: new Date(), updatedAt: new Date() },
      ];
    }

    const response = await api.get<GlossaryEntry[]>(`/glossary/${fileId}`);
    return response.data;
  },

  search: async (fileId: string, query: string): Promise<GlossaryEntry[]> => {
    if (config.useMockData) {
      return glossaryApi.list(fileId);
    }

    const response = await api.get<GlossaryEntry[]>(`/glossary/${fileId}/search?q=${query}`);
    return response.data;
  },

  update: async (entryId: number, data: { targetTerm?: string; context?: string }): Promise<GlossaryEntry> => {
    if (config.useMockData) {
      return {
        id: entryId,
        workId: 1,
        sourceTerm: 'test',
        targetTerm: data.targetTerm || 'prueba',
        context: data.context,
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    }

    const response = await api.put<GlossaryEntry>(`/glossary/${entryId}`, data);
    return response.data;
  },

  delete: async (entryId: number): Promise<void> => {
    if (config.useMockData) {
      return;
    }

    await api.delete(`/glossary/${entryId}`);
  },
};

export const translationApi = {
  get: async (fileId: string): Promise<TranslationData> => {
    if (config.useMockData) {
      return {
        fileId,
        chapters: [
          {
            chapterId: 1,
            chapterTitle: 'Chapter 1',
            chunks: [
              { id: 1, chapterId: 1, originalText: 'The old wizard stood at the edge of the cliff...', translatedText: 'El viejo mago estaba al borde del acantilado...', order: 1 },
            ],
          },
        ],
      };
    }

    const response = await api.get<TranslationData>(`/translation/${fileId}`);
    return response.data;
  },

  update: async (chunkId: number, translatedText: string): Promise<void> => {
    if (config.useMockData) {
      return;
    }

    await api.put(`/translation/${chunkId}`, { translatedText });
  },
};

export const audioApi = {
  generate: async (fileId: string): Promise<{ jobId: string }> => {
    if (config.useMockData) {
      return { jobId: `${fileId}-audio-job` };
    }

    const response = await api.post<{ jobId: string }>(`/audio/${fileId}/generate`);
    return response.data;
  },

  getStatus: async (fileId: string): Promise<AudioStatus> => {
    if (config.useMockData) {
      return {
        status: 'completed',
        progress: 100,
        audioFiles: [
          { chapterId: 1, chapterTitle: 'Chapter 1', format: 'm4a', duration: 300, url: '/audio/ch1.m4a', size: 2048576 },
        ],
      };
    }

    const response = await api.get<AudioStatus>(`/audio/${fileId}/status`);
    return response.data;
  },

  download: async (fileId: string, format: string): Promise<Blob> => {
    if (config.useMockData) {
      return new Blob(['mock audio data'], { type: 'audio/mp4' });
    }

    const response = await api.get(`/audio/${fileId}/download?format=${format}`, { responseType: 'blob' });
    return response.data;
  },
};

export default api;
```

**Step 4: Create .env.example**

Create `frontend/.env.example`:
```
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:8000/api
```

**Step 5: Create .env**

Create `frontend/.env`:
```
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:8000/api
```

**Step 6: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 7: Commit API service**

Run:
```bash
git add frontend/src/services/ frontend/.env*
git commit -m "feat: create API service layer with mock data support"
```

---

## Phase 3: Zustand Stores

### Task 3.1: Create File Store

**Files:**
- Create: `frontend/src/stores/fileStore.ts`

**Step 1: Create file store**

Create `frontend/src/stores/fileStore.ts`:
```typescript
import { create } from 'zustand';
import type { FileItem } from '../types';
import { fileApi } from '../services/api';

interface FileStore {
  files: FileItem[];
  selectedFileId: string | null;
  isLoading: boolean;
  error: string | null;
  addFiles: (files: File[]) => Promise<void>;
  removeFile: (id: string) => Promise<void>;
  selectFile: (id: string) => void;
  clearSelection: () => void;
  loadFiles: () => Promise<void>;
}

export const useFileStore = create<FileStore>((set, get) => ({
  files: [],
  selectedFileId: null,
  isLoading: false,
  error: null,

  addFiles: async (newFiles: File[]) => {
    set({ isLoading: true, error: null });
    try {
      const uploadedFiles = await fileApi.upload(newFiles);
      const fileItems: FileItem[] = uploadedFiles.map((f) => ({
        ...f,
        uploadedAt: new Date(f.uploadedAt),
      }));
      set((state) => ({
        files: [...state.files, ...fileItems],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to upload files',
        isLoading: false,
      });
      throw error;
    }
  },

  removeFile: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await fileApi.delete(id);
      set((state) => ({
        files: state.files.filter((f) => f.id !== id),
        selectedFileId: state.selectedFileId === id ? null : state.selectedFileId,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete file',
        isLoading: false,
      });
      throw error;
    }
  },

  selectFile: (id: string) => {
    set({ selectedFileId: id });
  },

  clearSelection: () => {
    set({ selectedFileId: null });
  },

  loadFiles: async () => {
    set({ isLoading: true, error: null });
    try {
      const files = await fileApi.list();
      set({ files, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load files',
        isLoading: false,
      });
    }
  },
}));
```

**Step 2: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 3: Commit file store**

Run:
```bash
git add frontend/src/stores/
git commit -m "feat: create Zustand file store"
```

---

### Task 3.2: Create Task Store

**Files:**
- Create: `frontend/src/stores/taskStore.ts`

**Step 1: Create task store**

Create `frontend/src/stores/taskStore.ts`:
```typescript
import { create } from 'zustand';
import type { TaskType, TaskStatus, TaskStatusEnum } from '../types';
import { taskApi } from '../services/api';

interface TaskStore {
  tasks: Record<string, TaskStatus>;
  isLoading: boolean;
  error: string | null;
  loadTaskStatus: (fileId: string) => Promise<void>;
  startTask: (fileId: string, taskType: TaskType) => Promise<void>;
  retryTask: (fileId: string, taskType: TaskType) => Promise<void>;
  updateTaskState: (fileId: string, taskType: TaskType, status: TaskStatusEnum, progress?: number, error?: string) => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: {},
  isLoading: false,
  error: null,

  loadTaskStatus: async (fileId: string) => {
    set({ isLoading: true, error: null });
    try {
      const status = await taskApi.getStatus(fileId);
      set((state) => ({
        tasks: { ...state.tasks, [fileId]: status },
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load task status',
        isLoading: false,
      });
    }
  },

  startTask: async (fileId: string, taskType: TaskType) => {
    set({ isLoading: true, error: null });
    try {
      await taskApi.start(fileId, taskType);
      get().updateTaskState(fileId, taskType, 'in-progress', 0);
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to start task',
        isLoading: false,
      });
      throw error;
    }
  },

  retryTask: async (fileId: string, taskType: TaskType) => {
    set({ isLoading: true, error: null });
    try {
      await taskApi.retry(fileId, taskType);
      get().updateTaskState(fileId, taskType, 'in-progress', 0);
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to retry task',
        isLoading: false,
      });
      throw error;
    }
  },

  updateTaskState: (fileId: string, taskType: TaskType, status: TaskStatusEnum, progress?: number, error?: string) => {
    set((state) => {
      const currentStatus = state.tasks[fileId] || {
        splitChapters: { status: 'pending', updatedAt: new Date() },
        glossary: { status: 'pending', updatedAt: new Date() },
        translated: { status: 'pending', updatedAt: new Date() },
        audioGenerated: { status: 'pending', updatedAt: new Date() },
      };

      const updatedTask = {
        status,
        updatedAt: new Date(),
        progress,
        error,
      };

      return {
        tasks: {
          ...state.tasks,
          [fileId]: {
            ...currentStatus,
            [taskType]: updatedTask,
          },
        },
      };
    });
  },
}));
```

**Step 2: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 3: Commit task store**

Run:
```bash
git add frontend/src/stores/
git commit -m "feat: create Zustand task store"
```

---

## Phase 4: Backend FastAPI Setup

### Task 4.1: Initialize FastAPI Project

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/api/__init__.py`
- Create: `backend/api/routes/__init__.py`
- Create: `backend/api/models/__init__.py`
- Create: `backend/api/services/__init__.py`

**Step 1: Create backend directory structure**

Run:
```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator
mkdir -p backend/api/routes backend/api/models backend/api/services
```

Expected: Creates backend directory structure

**Step 2: Create requirements.txt**

Create `backend/requirements.txt`:
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
```

**Step 3: Create main.py**

Create `backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PDFTranslator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PDFTranslator API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 4: Create __init__.py files**

Run:
```bash
touch backend/api/__init__.py
touch backend/api/routes/__init__.py
touch backend/api/models/__init__.py
touch backend/api/services/__init__.py
```

**Step 5: Test FastAPI server**

Run:
```bash
cd backend && python -m uvicorn main:app --reload
```

Expected: FastAPI server starts on port 8000, accessible at http://localhost:8000

**Step 6: Test endpoints**

Open browser to http://localhost:8000/docs

Expected: See FastAPI Swagger UI with GET / and GET /health endpoints

**Step 7: Stop server and commit**

Run:
```bash
git add backend/
git commit -m "feat: initialize FastAPI backend with CORS and health endpoints"
```

---

### Task 4.2: Create Pydantic Models

**Files:**
- Create: `backend/api/models/schemas.py`

**Step 1: Create Pydantic schemas**

Create `backend/api/models/schemas.py`:
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: str
    name: str
    size: int
    type: str
    uploaded_at: datetime
    work_id: int
    volume_id: int


class TaskStateSchema(BaseModel):
    status: str
    updated_at: datetime
    error: Optional[str] = None
    progress: Optional[int] = None


class TaskStatusResponse(BaseModel):
    split_chapters: TaskStateSchema
    glossary: TaskStateSchema
    translated: TaskStateSchema
    audio_generated: TaskStateSchema


class TaskStartRequest(BaseModel):
    task_type: str


class TaskStartResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ChapterResponse(BaseModel):
    id: int
    volume_id: int
    chapter_number: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChapterUpdateRequest(BaseModel):
    title: Optional[str] = None


class GlossaryEntryResponse(BaseModel):
    id: int
    work_id: int
    volume_id: Optional[int]
    source_term: str
    target_term: str
    context: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class GlossaryUpdateRequest(BaseModel):
    target_term: Optional[str] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class TranslationChunkResponse(BaseModel):
    id: int
    chapter_id: int
    original_text: str
    translated_text: str
    order: int


class TranslationChapterResponse(BaseModel):
    chapter_id: int
    chapter_title: str
    chunks: list[TranslationChunkResponse]


class TranslationDataResponse(BaseModel):
    file_id: str
    chapters: list[TranslationChapterResponse]


class TranslationUpdateRequest(BaseModel):
    translated_text: str


class AudioFileResponse(BaseModel):
    chapter_id: int
    chapter_title: str
    format: str
    duration: int
    url: str
    size: int


class AudioStatusResponse(BaseModel):
    status: str
    progress: int
    audio_files: Optional[list[AudioFileResponse]] = None
    error: Optional[str] = None
```

**Step 2: Verify Python syntax**

Run:
```bash
cd backend && python -c "from api.models.schemas import *; print('OK')"
```

Expected: Prints "OK" without errors

**Step 3: Commit schemas**

Run:
```bash
git add backend/api/models/
git commit -m "feat: create Pydantic schemas for API endpoints"
```

---

### Task 4.3: Create File Upload Endpoint

**Files:**
- Create: `backend/api/routes/files.py`
- Modify: `backend/main.py`

**Step 1: Create files route**

Create `backend/api/routes/files.py`:
```python
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import FileUploadResponse

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=List[FileUploadResponse])
async def upload_files(files: List[UploadFile] = File(...)):
    responses = []
    for file in files:
        allowed_extensions = {".pdf", ".epub", ".doc", ".docx"}
        file_ext = "." + file.filename.split(".")[-1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed types: {allowed_extensions}"
            )
        
        responses.append(
            FileUploadResponse(
                id=str(hash(file.filename + str(datetime.now()))),
                name=file.filename,
                size=0,
                type=file_ext[1:],
                uploaded_at=datetime.now(),
                work_id=hash(file.filename) % 10000,
                volume_id=hash(file.filename) % 10000,
            )
        )
    
    return responses


@router.get("/", response_model=List[FileUploadResponse])
async def list_files():
    return []


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(file_id: str):
    raise HTTPException(status_code=404, detail="File not found")


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    return {"message": "File deleted"}
```

**Step 2: Register route in main.py**

Edit `backend/main.py`, add before `if __name__ == "__main__"`:
```python
from api.routes import files

app.include_router(files.router)
```

**Step 3: Test file upload endpoint**

Run:
```bash
cd backend && python -m uvicorn main:app --reload
```

Open browser to http://localhost:8000/docs

Expected: See POST /api/files/upload endpoint

**Step 4: Commit files route**

Run:
```bash
git add backend/
git commit -m "feat: create file upload endpoint with validation"
```

---

## Phase 5: Frontend Dashboard

### Task 5.1: Create File Drop Zone Component

**Files:**
- Create: `frontend/src/components/ui/file-drop-zone.tsx`

**Step 1: Install additional shadcn/ui components**

Run:
```bash
cd frontend && npx shadcn-ui@latest add card
```

Expected: Creates `frontend/src/components/ui/card.tsx`

**Step 2: Create file drop zone**

Create `frontend/src/components/ui/file-drop-zone.tsx`:
```typescript
import React, { useCallback, useState } from 'react';
import { Card } from './card';

interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes?: string[];
}

const ACCEPTED_TYPES = ['.pdf', '.epub', '.doc', '.docx'];

export function FileDropZone({ onFilesSelected, acceptedTypes = ACCEPTED_TYPES }: FileDropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);

  const validateFiles = useCallback((files: FileList | null): File[] => {
    if (!files) return [];

    const validFiles: File[] = [];
    const errors: string[] = [];

    Array.from(files).forEach((file) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (acceptedTypes.includes(ext)) {
        validFiles.push(file);
      } else {
        errors.push(`${file.name} has invalid type. Allowed: ${acceptedTypes.join(', ')}`);
      }
    });

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    return validFiles;
  }, [acceptedTypes]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(false);
    const validFiles = validateFiles(e.dataTransfer.files);
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [validateFiles, onFilesSelected]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const validFiles = validateFiles(e.target.files);
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [validateFiles, onFilesSelected]);

  return (
    <Card
      className={`p-12 border-2 border-dashed cursor-pointer transition-all ${
        isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="flex flex-col items-center justify-center space-y-4">
        <svg
          className={`w-12 h-12 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="text-lg font-medium text-gray-700">
          Drop PDF, EPUB, DOC, or DOCX files here
        </p>
        <p className="text-sm text-gray-500">or click to browse</p>
        <input
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </Card>
  );
}
```

**Step 3: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 4: Commit file drop zone**

Run:
```bash
git add frontend/src/components/ui/
git commit -m "feat: create file drop zone component"
```

---

### Task 5.2: Create Task Badge Component

**Files:**
- Create: `frontend/src/components/ui/task-badge.tsx`

**Step 1: Create task badge**

Create `frontend/src/components/ui/task-badge.tsx`:
```typescript
import { Badge } from './badge';
import type { TaskState } from '../../types';

interface TaskBadgeProps {
  taskName: string;
  taskState: TaskState;
  onRetry?: () => void;
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-800',
  'in-progress': 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const statusIcons = {
  pending: '⏳',
  'in-progress': '⏳',
  completed: '✓',
  failed: '✗',
};

export function TaskBadge({ taskName, taskState, onRetry }: TaskBadgeProps) {
  const { status, progress, error } = taskState;

  return (
    <div className="flex items-center space-x-2">
      <Badge className={statusColors[status]}>
        <span className="mr-1">{statusIcons[status]}</span>
        {taskName}
        {status === 'in-progress' && progress !== undefined && ` (${progress}%)`}
      </Badge>
      {status === 'failed' && onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Retry
        </button>
      )}
      {status === 'failed' && error && (
        <span className="text-xs text-red-600" title={error}>
          {error.substring(0, 30)}...
        </span>
      )}
    </div>
  );
}
```

**Step 2: Install Badge component**

Run:
```bash
cd frontend && npx shadcn-ui@latest add badge
```

Expected: Creates `frontend/src/components/ui/badge.tsx`

**Step 3: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 4: Commit task badge**

Run:
```bash
git add frontend/src/components/ui/
git commit -m "feat: create task badge component with retry functionality"
```

---

### Task 5.3: Create File Card Component

**Files:**
- Create: `frontend/src/components/ui/file-card.tsx`

**Step 1: Create file card**

Create `frontend/src/components/ui/file-card.tsx`:
```typescript
import { Card } from './card';
import { TaskBadge } from './task-badge';
import type { FileItem, TaskStatus } from '../../types';

interface FileCardProps {
  file: FileItem;
  taskStatus?: TaskStatus;
  isSelected: boolean;
  onClick: () => void;
  onRetryTask: (taskType: string) => void;
}

const fileIcons: Record<string, string> = {
  pdf: '📄',
  epub: '📘',
  doc: '📝',
  docx: '📝',
};

export function FileCard({ file, taskStatus, isSelected, onClick, onRetryTask }: FileCardProps) {
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card
      className={`p-4 cursor-pointer transition-all ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'hover:shadow-md'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">{fileIcons[file.type]}</span>
          <div>
            <h3 className="font-medium text-gray-900">{file.name}</h3>
            <p className="text-sm text-gray-500">{formatSize(file.size)}</p>
          </div>
        </div>
      </div>

      {taskStatus && (
        <div className="space-y-2">
          <TaskBadge taskName="Chapters" taskState={taskStatus.splitChapters} />
          <TaskBadge taskName="Glossary" taskState={taskStatus.glossary} />
          <TaskBadge taskName="Translated" taskState={taskStatus.translated} />
          <TaskBadge
            taskName="Audio"
            taskState={taskStatus.audioGenerated}
            onRetry={() => onRetryTask('audioGenerated')}
          />
        </div>
      )}
    </Card>
  );
}
```

**Step 2: Verify TypeScript compilation**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors

**Step 3: Commit file card**

Run:
```bash
git add frontend/src/components/ui/
git commit -m "feat: create file card component with task badges"
```

---

### Task 5.4: Create Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`

**Step 1: Create Dashboard page**

Create `frontend/src/pages/Dashboard.tsx`:
```typescript
import { useEffect } from 'react';
import { FileDropZone } from '../components/ui/file-drop-zone';
import { FileCard } from '../components/ui/file-card';
import { useFileStore } from '../stores/fileStore';
import { useTaskStore } from '../stores/taskStore';

export function Dashboard() {
  const { files, selectedFileId, addFiles, selectFile, loadFiles } = useFileStore();
  const { tasks, loadTaskStatus, retryTask } = useTaskStore();

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  useEffect(() => {
    files.forEach((file) => {
      if (!tasks[file.id]) {
        loadTaskStatus(file.id);
      }
    });
  }, [files, tasks, loadTaskStatus]);

  const handleFilesSelected = async (newFiles: File[]) => {
    try {
      await addFiles(newFiles);
    } catch (error) {
      console.error('Failed to upload files:', error);
      alert('Failed to upload files. Please try again.');
    }
  };

  const handleRetryTask = async (fileId: string, taskType: string) => {
    try {
      await retryTask(fileId, taskType as any);
    } catch (error) {
      console.error('Failed to retry task:', error);
      alert('Failed to retry task. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">PDFTranslator</h1>
          <p className="mt-2 text-gray-600">Document Workflow Dashboard</p>
        </div>

        <div className="mb-8">
          <FileDropZone onFilesSelected={handleFilesSelected} />
        </div>

        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Files ({files.length})
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {files.map((file) => (
            <FileCard
              key={file.id}
              file={file}
              taskStatus={tasks[file.id]}
              isSelected={selectedFileId === file.id}
              onClick={() => selectFile(file.id)}
              onRetryTask={(taskType) => handleRetryTask(file.id, taskType)}
            />
          ))}
        </div>

        {files.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No files uploaded yet. Drop files above to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Update App.tsx with routing**

Edit `frontend/src/App.tsx`:
```typescript
import { Dashboard } from './pages/Dashboard';

function App() {
  return <Dashboard />;
}

export default App;
```

**Step 3: Update index.css**

Edit `frontend/src/index.css`, add at the end:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

**Step 4: Test Dashboard**

Run:
```bash
cd frontend && npm run dev
```

Open browser to http://localhost:5173

Expected: See Dashboard with file drop zone and mock files displayed

**Step 5: Commit Dashboard**

Run:
```bash
git add frontend/src/
git commit -m "feat: create Dashboard page with file upload and list"
```

---

## Phase 6: Task Screens (Basic Structure)

### Task 6.1: Setup React Router

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/TaskLayout.tsx`

**Step 1: Install React Router types**

Run:
```bash
cd frontend && npm install @types/react-router-dom
```

**Step 2: Create TaskLayout**

Create `frontend/src/pages/TaskLayout.tsx`:
```typescript
import { Outlet, Link, useParams } from 'react-router-dom';
import { useFileStore } from '../stores/fileStore';

export function TaskLayout() {
  const { fileId } = useParams<{ fileId: string }>();
  const { files } = useFileStore();
  const file = files.find((f) => f.id === fileId);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link to="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Dashboard
          </Link>
          {file && (
            <h1 className="text-2xl font-bold text-gray-900 mt-4">
              {file.name}
            </h1>
          )}
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </div>
    </div>
  );
}
```

**Step 3: Update App with Router**

Edit `frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { TaskLayout } from './pages/TaskLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/file/:fileId" element={<TaskLayout />}>
          <Route path="chapters" element={<div>Chapters Screen (TODO)</div>} />
          <Route path="glossary" element={<div>Glossary Screen (TODO)</div>} />
          <Route path="translated" element={<div>Translated Screen (TODO)</div>} />
          <Route path="audio" element={<div>Audio Screen (TODO)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

**Step 4: Update file card to navigate**

Edit `frontend/src/components/ui/file-card.tsx`, modify onClick:
```typescript
import { useNavigate } from 'react-router-dom';

export function FileCard({ file, taskStatus, isSelected, onRetryTask }: FileCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/file/${file.id}/chapters`);
  };

  return (
    <Card
      className={`p-4 cursor-pointer transition-all ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'hover:shadow-md'
      }`}
      onClick={handleClick}
    >
      {/* ... rest of component */}
    </Card>
  );
}
```

**Step 5: Test routing**

Run:
```bash
cd frontend && npm run dev
```

Click on a file card

Expected: Navigates to /file/{id}/chapters with "Chapters Screen (TODO)"

**Step 6: Commit routing**

Run:
```bash
git add frontend/src/
git commit -m "feat: setup React Router with task layout"
```

---

### Task 6.2: Create Split Chapters Screen (Basic)

**Files:**
- Create: `frontend/src/pages/SplitChaptersScreen.tsx`

**Step 1: Create SplitChaptersScreen**

Create `frontend/src/pages/SplitChaptersScreen.tsx`:
```typescript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '../components/ui/card';
import type { Chapter } from '../types';
import { chapterApi } from '../services/api';

export function SplitChaptersScreen() {
  const { fileId } = useParams<{ fileId: string }>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!fileId) return;

    const loadChapters = async () => {
      try {
        const data = await chapterApi.list(fileId);
        setChapters(data);
      } catch (error) {
        console.error('Failed to load chapters:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadChapters();
  }, [fileId]);

  if (isLoading) {
    return <div className="text-center py-12">Loading chapters...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          Chapter Breakdown ({chapters.length} chapters detected)
        </h2>
      </div>

      <div className="space-y-4">
        {chapters.map((chapter) => (
          <Card key={chapter.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{chapter.title}</h3>
                <p className="text-sm text-gray-500">
                  Chapter {chapter.chapterNumber}
                </p>
              </div>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Preview
                </button>
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Edit Title
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-6 flex space-x-4">
        <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
          Run Auto-Detection Again
        </button>
        <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Approve & Continue
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Update App routing**

Edit `frontend/src/App.tsx`, import and use SplitChaptersScreen:
```typescript
import { SplitChaptersScreen } from './pages/SplitChaptersScreen';

// In Routes:
<Route path="chapters" element={<SplitChaptersScreen />} />
```

**Step 3: Test Split Chapters screen**

Run:
```bash
cd frontend && npm run dev
```

Navigate to a file's chapters tab

Expected: See list of chapters with Preview and Edit Title buttons

**Step 4: Commit Split Chapters screen**

Run:
```bash
git add frontend/src/
git commit -m "feat: create basic Split Chapters screen"
```

---

### Task 6.3: Create Glossary Screen (Basic)

**Files:**
- Create: `frontend/src/pages/GlossaryScreen.tsx`

**Step 1: Install Input component**

Run:
```bash
cd frontend && npx shadcn-ui@latest add input
```

**Step 2: Create GlossaryScreen**

Create `frontend/src/pages/GlossaryScreen.tsx`:
```typescript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import type { GlossaryEntry } from '../types';
import { glossaryApi } from '../services/api';

export function GlossaryScreen() {
  const { fileId } = useParams<{ fileId: string }>();
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!fileId) return;

    const loadGlossary = async () => {
      try {
        const data = await glossaryApi.list(fileId);
        setEntries(data);
      } catch (error) {
        console.error('Failed to load glossary:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadGlossary();
  }, [fileId]);

  const handleSearch = async () => {
    if (!fileId || !searchQuery) return;

    try {
      const data = await glossaryApi.search(fileId, searchQuery);
      setEntries(data);
    } catch (error) {
      console.error('Failed to search glossary:', error);
    }
  };

  const filteredEntries = searchQuery
    ? entries.filter(
        (e) =>
          e.sourceTerm.includes(searchQuery) || e.targetTerm.includes(searchQuery)
      )
    : entries;

  if (isLoading) {
    return <div className="text-center py-12">Loading glossary...</div>;
  }

  return (
    <div>
      <div className="mb-6 flex space-x-4">
        <Input
          type="text"
          placeholder="Search terms..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Search
        </button>
        <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
          Add Term
        </button>
      </div>

      <div className="space-y-4">
        {filteredEntries.map((entry) => (
          <Card key={entry.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-gray-900">{entry.sourceTerm}</div>
                <div className="text-blue-600 mt-1">→ {entry.targetTerm}</div>
                {entry.context && (
                  <div className="text-sm text-gray-500 mt-2">
                    Context: "{entry.context}"
                  </div>
                )}
              </div>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Edit
                </button>
                <button className="px-3 py-1 text-sm text-red-600 hover:text-red-800">
                  Delete
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filteredEntries.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No glossary entries found.
        </div>
      )}
    </div>
  );
}
```

**Step 3: Update App routing**

Edit `frontend/src/App.tsx`:
```typescript
import { GlossaryScreen } from './pages/GlossaryScreen';

// In Routes:
<Route path="glossary" element={<GlossaryScreen />} />
```

**Step 4: Test Glossary screen**

Run:
```bash
cd frontend && npm run dev
```

Navigate to a file's glossary tab

Expected: See glossary entries with search functionality

**Step 5: Commit Glossary screen**

Run:
```bash
git add frontend/src/
git commit -m "feat: create basic Glossary screen with search"
```

---

## Phase 7: Testing & Polish

### Task 7.1: Add Error Boundary

**Files:**
- Create: `frontend/src/components/ErrorBoundary.tsx`

**Step 1: Create Error Boundary**

Create `frontend/src/components/ErrorBoundary.tsx`:
```typescript
import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Something went wrong
            </h1>
            <p className="text-gray-600 mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

**Step 2: Wrap App with Error Boundary**

Edit `frontend/src/main.tsx`:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { ErrorBoundary } from './components/ErrorBoundary';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
```

**Step 3: Test error boundary**

Run:
```bash
cd frontend && npm run dev
```

Expected: App loads normally, error boundary catches any errors

**Step 4: Commit error boundary**

Run:
```bash
git add frontend/src/
git commit -m "feat: add error boundary for graceful error handling"
```

---

### Task 7.2: Add Loading States

**Files:**
- Create: `frontend/src/components/ui/spinner.tsx`

**Step 1: Create Spinner component**

Create `frontend/src/components/ui/spinner.tsx`:
```typescript
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`${sizeClasses[size]} animate-spin`}>
      <svg className="w-full h-full" viewBox="0 0 24 24">
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 2.198.645 4.244 1.75 5.941l2.25-2.65z"
        />
      </svg>
    </div>
  );
}
```

**Step 2: Use Spinner in Dashboard**

Edit `frontend/src/pages/Dashboard.tsx`, add loading state:
```typescript
import { Spinner } from '../components/ui/spinner';

// In Dashboard component:
const { files, selectedFileId, addFiles, selectFile, loadFiles, isLoading } = useFileStore();

// Add loading check:
if (isLoading) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}
```

**Step 3: Commit loading states**

Run:
```bash
git add frontend/src/
git commit -m "feat: add spinner and loading states"
```

---

### Task 7.3: Create README for Frontend

**Files:**
- Create: `frontend/README.md`

**Step 1: Create README**

Create `frontend/README.md`:
```markdown
# PDFTranslator Frontend

React-based web UI for PDFTranslator document processing workflow.

## Tech Stack

- React 18 + TypeScript (strict mode)
- Vite (build tool)
- Zustand (state management)
- shadcn/ui (component library)
- Tailwind CSS
- React Router (routing)

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npx tsc --noEmit
```

## Environment Variables

Create `.env` file:

```
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:8000/api
```

## Project Structure

```
src/
├── components/
│   ├── containers/     # Logic-heavy components
│   └── ui/             # Presentational components (shadcn/ui)
├── pages/              # Route pages
├── stores/             # Zustand state stores
├── services/           # API abstraction layer
├── hooks/              # Custom React hooks
├── types/              # TypeScript types
└── lib/                # Utilities
```

## Features

- File upload (drag & drop + manual selection)
- File type validation (PDF, EPUB, DOC, DOCX)
- Task status tracking (pending, in-progress, completed, failed)
- Split Chapters screen
- Glossary screen with search/filter
- Translated screen (side-by-side view)
- Audio screen with player

## Testing

```bash
# Run tests (TODO: add test setup)
npm test
```

## Notes

- Mock data enabled by default (set `VITE_USE_MOCK_DATA=false` to use real API)
- Backend API must be running on http://localhost:8000
- TypeScript strict mode enabled
```

**Step 2: Commit README**

Run:
```bash
git add frontend/README.md
git commit -m "docs: add frontend README"
```

---

### Task 7.4: Final Commit and Push

**Step 1: Review all changes**

Run:
```bash
git status
git log --oneline -10
```

Expected: See all commits in feature branch

**Step 2: Push to remote**

Run:
```bash
git push -u origin feature/document-workflow-ui
```

Expected: Pushes feature branch to remote

**Step 3: Verify branch**

Run:
```bash
git branch -a
```

Expected: See feature/document-workflow-ui in branch list

---

## Summary

This implementation plan creates:

1. ✅ Frontend project structure with React + TypeScript + Vite
2. ✅ Zustand stores for file and task state management
3. ✅ API service layer with mock data support
4. ✅ FastAPI backend with file upload endpoint
5. ✅ Dashboard page with file upload and list
6. ✅ Task badge components with retry functionality
7. ✅ Basic Split Chapters and Glossary screens
8. ✅ Error boundary and loading states
9. ✅ Documentation and README

**Next Steps** (Future Tasks):
- Implement Translated screen with side-by-side view
- Implement Audio screen with player
- Add inline editing for chapters and glossary
- Create comprehensive test suite
- Add animations and micro-interactions
- Deploy to production

**All changes are in feature/document-workflow-ui branch with no modifications to stable code.**
