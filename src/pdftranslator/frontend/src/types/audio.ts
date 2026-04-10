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
