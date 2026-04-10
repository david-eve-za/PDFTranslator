export interface Chapter {
  id: number;
  volumeId: number;
  chapterNumber: number;
  title: string;
  startPage?: number;
  endPage?: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface ChapterUpdate {
  title?: string;
  mergeWithPrevious?: boolean;
}
