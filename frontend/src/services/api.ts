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
