export interface TranslationRequest {
  file: File;
  sourceLanguage: string;
  targetLanguage: string;
  provider?: string;
}

export interface TranslationResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  downloadUrl?: string;
  error?: string;
}

export interface Language {
  code: string;
  name: string;
  nativeName?: string;
}

export interface Provider {
  id: string;
  name: string;
  description?: string;
}

export interface GlossaryTerm {
  id: number;
  sourceTerm: string;
  targetTerm: string;
  sourceLanguage: string;
  targetLanguage: string;
  context?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface GlossaryCreateRequest {
  sourceTerm: string;
  targetTerm: string;
  sourceLanguage: string;
  targetLanguage: string;
  context?: string;
}

export interface GlossaryUpdateRequest extends GlossaryCreateRequest {
  id: number;
}
