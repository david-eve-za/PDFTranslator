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
