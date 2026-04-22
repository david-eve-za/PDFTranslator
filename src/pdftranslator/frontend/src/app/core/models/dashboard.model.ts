export interface DashboardStats {
  total_works: number;
  total_glossary_terms: number;
  translations_this_week: number;
  average_progress: number;
}

export interface RecentActivity {
  id: string;
  type: 'translation' | 'glossary' | 'import' | 'split';
  action: string;
  work_title?: string;
  timestamp: Date;
}

export interface TranslationChartData {
  completed: number;
  in_progress: number;
  pending: number;
}
