import { Work, Volume, Chapter, GlossaryTerm, TranslationProgress, RecentActivity } from '../models';

export const MOCK_WORKS: Work[] = [
  {
    id: 1,
    title: 'The Great Adventure',
    title_translated: 'La Gran Aventura',
    author: 'John Smith',
    volumes: [],
    total_chapters: 45,
    translated_chapters: 30,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-03-20')
  },
  {
    id: 2,
    title: 'Mystery of the Ancients',
    author: 'Jane Doe',
    volumes: [],
    total_chapters: 60,
    translated_chapters: 0,
    created_at: new Date('2025-02-10'),
    updated_at: new Date('2026-04-01')
  },
  {
    id: 3,
    title: 'Dragon\'s Legacy',
    title_translated: 'El Legado del Dragón',
    author: 'Carlos Writer',
    volumes: [],
    total_chapters: 120,
    translated_chapters: 120,
    created_at: new Date('2024-12-01'),
    updated_at: new Date('2026-02-28')
  }
];

export const MOCK_VOLUMES: Volume[] = [
  {
    id: 1,
    work_id: 1,
    volume_number: 1,
    chapters: [],
    full_text: 'Volume 1 full text...',
    created_at: new Date('2025-01-15')
  },
  {
    id: 2,
    work_id: 1,
    volume_number: 2,
    chapters: [],
    full_text: 'Volume 2 full text...',
    created_at: new Date('2025-01-20')
  },
  {
    id: 3,
    work_id: 2,
    volume_number: 1,
    chapters: [],
    created_at: new Date('2025-02-10')
  },
  {
    id: 4,
    work_id: 3,
    volume_number: 1,
    chapters: [],
    full_text: 'Dragon\'s Legacy Vol 1...',
    created_at: new Date('2024-12-01')
  },
  {
    id: 5,
    work_id: 3,
    volume_number: 2,
    chapters: [],
    full_text: 'Dragon\'s Legacy Vol 2...',
    created_at: new Date('2024-12-15')
  }
];

export const MOCK_CHAPTERS: Chapter[] = [
  {
    id: 1,
    volume_id: 1,
    chapter_number: 0,
    title: 'Prologue',
    chapter_type: 'prologue',
    original_text: 'In the beginning...',
    translated_text: 'Al principio...',
    is_translated: true,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-01-10')
  },
  {
    id: 2,
    volume_id: 1,
    chapter_number: 1,
    title: 'The Journey Begins',
    chapter_type: 'chapter',
    original_text: 'Chapter 1 content...',
    translated_text: 'Capítulo 1 contenido...',
    is_translated: true,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2026-01-12')
  },
  {
    id: 3,
    volume_id: 1,
    chapter_number: 2,
    title: 'Into the Forest',
    chapter_type: 'chapter',
    original_text: 'Chapter 2 content...',
    is_translated: false,
    created_at: new Date('2025-01-15'),
    updated_at: new Date('2025-01-15')
  },
  {
    id: 4,
    volume_id: 2,
    chapter_number: 1,
    title: 'New Horizons',
    chapter_type: 'chapter',
    original_text: 'Chapter 1 of vol 2...',
    is_translated: false,
    created_at: new Date('2025-01-20'),
    updated_at: new Date('2025-01-20')
  },
  {
    id: 5,
    volume_id: 3,
    chapter_number: 1,
    title: 'The First Mystery',
    chapter_type: 'chapter',
    original_text: 'Mystery chapter 1...',
    is_translated: false,
    created_at: new Date('2025-02-10'),
    updated_at: new Date('2025-02-10')
  }
];

export const MOCK_GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    id: 1,
    work_id: 1,
    term: 'Elena',
    translation: 'Elena',
    entity_type: 'character',
    context: 'Main protagonist',
    is_proper_noun: true,
    frequency: 150,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-15')
  },
  {
    id: 2,
    work_id: 1,
    term: 'Crystal Kingdom',
    translation: 'Reino de Cristal',
    entity_type: 'place',
    context: 'Main setting',
    is_proper_noun: true,
    frequency: 80,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-15')
  },
  {
    id: 3,
    work_id: 1,
    term: 'Fireball',
    translation: 'Bola de fuego',
    entity_type: 'spell',
    context: 'Common fire spell',
    is_proper_noun: false,
    frequency: 45,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-20')
  },
  {
    id: 4,
    work_id: 1,
    term: 'Shadow Guild',
    translation: 'Gremio de las Sombras',
    entity_type: 'faction',
    context: 'Antagonist group',
    is_proper_noun: true,
    frequency: 60,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-01'),
    updated_at: new Date('2026-01-18')
  },
  {
    id: 5,
    work_id: 2,
    term: 'Ancient Temple',
    translation: 'Templo Ancestral',
    entity_type: 'place',
    context: 'Central location',
    is_proper_noun: true,
    frequency: 90,
    source_lang: 'en',
    target_lang: 'es',
    created_at: new Date('2025-02-15'),
    updated_at: new Date('2025-02-15')
  }
];

export const MOCK_TRANSLATION_PROGRESS: TranslationProgress[] = [
  {
    id: 'trans-1',
    work_id: 1,
    scope: 'all_volume',
    volume_id: 1,
    status: 'in_progress',
    total_chunks: 150,
    completed_chunks: 45,
    current_chunk: 'Chapter 2, paragraph 12',
    started_at: new Date('2026-04-10T10:00:00'),
  }
];

export const MOCK_RECENT_ACTIVITIES: RecentActivity[] = [
  {
    id: 'act-1',
    type: 'translation',
    action: 'Translation completed',
    work_title: 'Dragon\'s Legacy',
    timestamp: new Date('2026-04-10T14:30:00')
  },
  {
    id: 'act-2',
    type: 'glossary',
    action: 'Term added: Shadow Guild',
    work_title: 'The Great Adventure',
    timestamp: new Date('2026-04-10T13:15:00')
  },
  {
    id: 'act-3',
    type: 'import',
    action: 'Work imported',
    work_title: 'Mystery of the Ancients',
    timestamp: new Date('2026-04-09T16:00:00')
  },
  {
    id: 'act-4',
    type: 'split',
    action: 'Chapters split',
    work_title: 'The Great Adventure - Vol 1',
    timestamp: new Date('2026-04-09T10:30:00')
  },
  {
    id: 'act-5',
    type: 'translation',
    action: 'Translation started',
    work_title: 'The Great Adventure',
    timestamp: new Date('2026-04-10T10:00:00')
  }
];

export const MOCK_LANGUAGES = [
  { code: 'en-US', name: 'English (US)' },
  { code: 'en-GB', name: 'English (UK)' },
  { code: 'es-ES', name: 'Spanish (Spain)' },
  { code: 'es-MX', name: 'Spanish (Mexico)' },
  { code: 'fr-FR', name: 'French' },
  { code: 'de-DE', name: 'German' },
  { code: 'it-IT', name: 'Italian' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)' },
  { code: 'ja-JP', name: 'Japanese' },
  { code: 'zh-CN', name: 'Chinese (Simplified)' },
  { code: 'ko-KR', name: 'Korean' },
  { code: 'ru-RU', name: 'Russian' }
];

export const MOCK_PROVIDERS = [
  { id: 'nvidia', name: 'NVIDIA', description: 'NVIDIA NIM API for fast, accurate translations' },
  { id: 'gemini', name: 'Gemini', description: 'Google Gemini for high-quality translations' },
  { id: 'ollama', name: 'Ollama', description: 'Local LLM for privacy-focused translations' }
];
