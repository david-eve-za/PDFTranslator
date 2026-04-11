export type ChapterType = 'prologue' | 'chapter' | 'epilogue';
export type TranslationStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface Chapter {
  id: number;
  volume_id: number;
  chapter_number: number;
  title: string;
  chapter_type: ChapterType;
  original_text?: string;
  translated_text?: string;
  is_translated: boolean;
  start_position?: number;
  end_position?: number;
  created_at: Date;
  updated_at: Date;
}

export interface ChapterCreate {
  volume_id: number;
  chapter_number: number;
  title: string;
  chapter_type: ChapterType;
  original_text?: string;
}
