export interface Work {
  id: number;
  title: string;
  title_translated?: string;
  author: string;
  volumes: Volume[];
  total_chapters: number;
  translated_chapters: number;
  created_at: Date;
  updated_at: Date;
}

export interface WorkCreate {
  title: string;
  author: string;
}

export interface WorkUpdate {
  title?: string;
  title_translated?: string;
  author?: string;
}

import { Volume } from './volume.model';
