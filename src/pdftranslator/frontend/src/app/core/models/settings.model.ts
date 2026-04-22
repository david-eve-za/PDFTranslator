export interface LLMSettings {
  agent: string;
  nvidia: {
    model_name: string;
    temperature: number;
    top_p: number;
    max_output_tokens: number;
  };
  gemini: {
    model_names: string[];
    temperature: number;
    top_p: number;
  };
  ollama: {
    model_name: string;
    temperature: number;
  };
  nvidia_api_key: string;
  google_api_key: string;
}

export interface DatabaseSettings {
  host: string;
  port: number;
  name: string;
  user: string;
  password: string;
  min_connections: number;
  max_connections: number;
}

export interface DocumentSettings {
  enable_ocr: boolean;
  ocr_languages: string[];
  accelerator_device: string;
  do_table_structure: boolean;
  generate_page_images: boolean;
}

export interface NLPSettings {
  ner_model: string;
  entity_types: string[];
  min_entity_length: number;
  max_entity_length: number;
  confidence_threshold: number;
}

export interface PathSettings {
  translation_prompt_path: string;
  audiobooks_dir: string;
  videos_dir: string;
}

export interface Settings {
  llm: LLMSettings;
  database: DatabaseSettings;
  document: DocumentSettings;
  nlp: NLPSettings;
  paths: PathSettings;
}

export interface SettingsUpdateRequest {
  llm?: Partial<LLMSettings>;
  database?: Partial<DatabaseSettings>;
  document?: Partial<DocumentSettings>;
  nlp?: Partial<NLPSettings>;
  paths?: Partial<PathSettings>;
}
