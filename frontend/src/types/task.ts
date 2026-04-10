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
