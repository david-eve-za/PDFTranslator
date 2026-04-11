import { Injectable } from '@angular/core';
import { InMemoryDbService } from 'angular-in-memory-web-api';
import {
  MOCK_WORKS,
  MOCK_VOLUMES,
  MOCK_CHAPTERS,
  MOCK_GLOSSARY_TERMS,
  MOCK_TRANSLATION_PROGRESS,
  MOCK_RECENT_ACTIVITIES,
  MOCK_LANGUAGES,
  MOCK_PROVIDERS
} from './mock-data';

@Injectable({
  providedIn: 'root'
})
export class InMemoryDataService implements InMemoryDbService {
  createDb() {
    return {
      works: MOCK_WORKS,
      volumes: MOCK_VOLUMES,
      chapters: MOCK_CHAPTERS,
      glossaryTerms: MOCK_GLOSSARY_TERMS,
      translationProgress: MOCK_TRANSLATION_PROGRESS,
      recentActivities: MOCK_RECENT_ACTIVITIES,
      languages: MOCK_LANGUAGES,
      providers: MOCK_PROVIDERS
    };
  }

  genId<T>(collection: T[]): number {
    return collection.length > 0 ? Math.max(...collection.map((item: any) => item.id)) + 1 : 1;
  }
}
