export type TranslationScope = 'all_book' | 'all_volume' | 'single_chapter';
export type ProgressStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface TranslationProgress {
  id: string;
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  status: ProgressStatus;
  total_chunks: number;
  completed_chunks: number;
  current_chunk?: string;
  started_at?: Date;
  completed_at?: Date;
  error?: string;
}

export interface TranslationStartRequest {
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  source_lang: string;
  target_lang: string;
  provider: string;
}
