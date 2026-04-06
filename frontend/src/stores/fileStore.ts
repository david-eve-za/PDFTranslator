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
