export interface TranslationChunk {
  id: number;
  chapterId: number;
  originalText: string;
  translatedText: string;
  order: number;
}

export interface TranslationData {
  fileId: string;
  chapters: TranslationChapter[];
}

export interface TranslationChapter {
  chapterId: number;
  chapterTitle: string;
  chunks: TranslationChunk[];
}

export interface TranslationUpdate {
  chunkId: number;
  translatedText: string;
}
