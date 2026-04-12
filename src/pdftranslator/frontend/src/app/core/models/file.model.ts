export interface FileUploadResponse {
  id: number;
  filename: string;
  original_name: string;
  file_size: number;
  file_type: string;
  work_id: number | null;
  work_title: string | null;
  volume_id: number | null;
  volume_number: number | null;
  status: string;
  created_at: string;
}

export interface FileListResponse {
  items: FileUploadResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface FileUploadQuery {
  source_lang?: string;
  target_lang?: string;
}

export interface FileDeleteResponse {
  message: string;
  id: number;
}

export type FileStatus = 'pending' | 'processing' | 'done' | 'error';

export function getFileStatusColor(status: FileStatus): string {
  const colors: Record<FileStatus, string> = {
    pending: 'var(--warning)',
    processing: 'var(--primary)',
    done: 'var(--success)',
    error: 'var(--error)',
  };
  return colors[status] || 'var(--text-secondary)';
}

export function getFileStatusIcon(status: FileStatus): string {
  const icons: Record<FileStatus, string> = {
    pending: '⏳',
    processing: '⚡',
    done: '✓',
    error: '✕',
  };
  return icons[status] || '?';
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
