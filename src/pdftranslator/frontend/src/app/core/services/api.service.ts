import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';
import {
  Language,
  Provider,
  GlossaryTerm,
  GlossaryCreateRequest,
  GlossaryUpdateRequest,
  TranslationResponse,
} from '../models/translation.models';

export interface ProgressEvent {
  type: 'upload' | 'download';
  loaded: number;
  total: number;
  percentage: number;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(private http: HttpClient) {}

  getLanguages(): Observable<Language[]> {
    return this.http.get<Language[]>('/api/languages');
  }

  getProviders(): Observable<Provider[]> {
    return this.http.get<Provider[]>('/api/providers');
  }

  translateFile(
    file: File,
    sourceLanguage: string,
    targetLanguage: string,
    provider?: string,
    progressCallback?: (event: ProgressEvent) => void
  ): Observable<TranslationResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('sourceLanguage', sourceLanguage);
    formData.append('targetLanguage', targetLanguage);
    if (provider) {
      formData.append('provider', provider);
    }

    return this.http.post<TranslationResponse>('/api/translate', formData, {
      reportProgress: true,
      observe: 'events',
    }).pipe(
      tap((event: HttpEvent<TranslationResponse>) => {
        if (progressCallback && event.type === HttpEventType.UploadProgress) {
          const progress: ProgressEvent = {
            type: 'upload',
            loaded: event.loaded,
            total: event.total || 0,
            percentage: event.total
              ? Math.round((event.loaded / event.total) * 100)
              : 0,
          };
          progressCallback(progress);
        }
      }),
      map((event: HttpEvent<TranslationResponse>) => {
        if (event.type === HttpEventType.Response) {
          return event.body as TranslationResponse;
        }
        return {
          id: '',
          status: 'pending',
          progress: 0,
        };
      })
    );
  }

  getTranslationStatus(id: string): Observable<TranslationResponse> {
    return this.http.get<TranslationResponse>(`/api/translate/${id}`);
  }

  getGlossaryTerms(): Observable<GlossaryTerm[]> {
    return this.http.get<GlossaryTerm[]>('/api/glossary');
  }

  createGlossaryTerm(term: GlossaryCreateRequest): Observable<GlossaryTerm> {
    return this.http.post<GlossaryTerm>('/api/glossary', term);
  }

  updateGlossaryTerm(term: GlossaryUpdateRequest): Observable<GlossaryTerm> {
    return this.http.put<GlossaryTerm>(`/api/glossary/${term.id}`, term);
  }

  deleteGlossaryTerm(id: number): Observable<void> {
    return this.http.delete<void>(`/api/glossary/${id}`);
  }
}
