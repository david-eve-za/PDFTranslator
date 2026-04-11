export interface Volume {
  id: number;
  work_id: number;
  volume_number: number;
  chapters: Chapter[];
  full_text?: string;
  translated_text?: string;
  created_at: Date;
}

export interface VolumeCreate {
  work_id: number;
  volume_number: number;
  full_text?: string;
}

import { Chapter } from './chapter.model';
