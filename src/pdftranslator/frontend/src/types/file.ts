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
