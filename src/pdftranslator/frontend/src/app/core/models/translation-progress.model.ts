export type TranslationScope = 'all_book' | 'all_volume' | 'single_chapter';

export interface TranslationStartRequest {
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  source_lang: string;
  target_lang: string;
  skip_translated: boolean;
  dry_run: boolean;
}

export interface TranslationJobStatus {
  id: number;
  work_id: number;
  scope: TranslationScope;
  volume_id?: number;
  chapter_id?: number;
  source_lang: string;
  target_lang: string;
  skip_translated: boolean;
  dry_run: boolean;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  total_chapters: number;
  completed_chapters: number;
  success_count: number;
  failure_count: number;
  current_chapter_info?: string;
  error_message?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TranslationProgressEvent {
  event_type: 'progress' | 'chapter_complete' | 'job_complete' | 'error';
  completed_chapters?: number;
  total_chapters?: number;
  current?: string;
  chapter_id?: number;
  title?: string;
  chapter_status?: string;
  success_count?: number;
  failure_count?: number;
  message?: string;
}

export interface TranslationJobListResponse {
  items: TranslationJobStatus[];
  total: number;
}
