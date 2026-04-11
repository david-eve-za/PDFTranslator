export type EntityType = 'character' | 'place' | 'skill' | 'item' | 'spell' | 'faction' | 'title' | 'race' | 'other';

export interface GlossaryTerm {
  id: number;
  work_id: number;
  term: string;
  translation?: string;
  entity_type: EntityType;
  context?: string;
  is_proper_noun: boolean;
  frequency: number;
  source_lang: string;
  target_lang: string;
  created_at: Date;
  updated_at: Date;
}

export interface GlossaryTermCreate {
  work_id: number;
  term: string;
  translation?: string;
  entity_type: EntityType;
  context?: string;
  is_proper_noun: boolean;
  source_lang: string;
  target_lang: string;
}

export interface GlossaryTermUpdate {
  term?: string;
  translation?: string;
  entity_type?: EntityType;
  context?: string;
  is_proper_noun?: boolean;
}
