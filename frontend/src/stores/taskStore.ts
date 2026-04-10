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
