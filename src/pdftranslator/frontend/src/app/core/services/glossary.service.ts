import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GlossaryTerm, GlossaryTermCreate, GlossaryTermUpdate, EntityType } from '../models';

export interface GlossaryBuildRequest {
  work_id: number;
  source_lang?: string;
  target_lang?: string;
}

export interface GlossaryBuildVolumeResult {
  volume_id: number;
  volume_number: number;
  extracted: number;
  new: number;
  skipped: number;
  entities_by_type: Record<string, number>;
}

export interface GlossaryBuildResponse {
  total_extracted: number;
  total_new: number;
  total_skipped: number;
  volumes_processed: number;
  volumes_skipped: number;
  entities_by_type: Record<string, number>;
  volume_results: GlossaryBuildVolumeResult[];
}

@Injectable({
  providedIn: 'root'
})
export class GlossaryService {
  private apiUrl = '/api/glossary';

  constructor(private http: HttpClient) {}

  getAll(workId?: number, entityType?: EntityType): Observable<GlossaryTerm[]> {
    let params = new HttpParams();
    if (workId) params = params.set('work_id', workId.toString());
    return this.http.get<GlossaryTerm[]>(this.apiUrl, { params });
  }

  getById(id: number): Observable<GlossaryTerm> {
    return this.http.get<GlossaryTerm>(`${this.apiUrl}/${id}`);
  }

  create(term: GlossaryTermCreate): Observable<GlossaryTerm> {
    return this.http.post<GlossaryTerm>(this.apiUrl, term);
  }

  update(id: number, term: GlossaryTermUpdate): Observable<GlossaryTerm> {
    return this.http.put<GlossaryTerm>(`${this.apiUrl}/${id}`, term);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  build(request: GlossaryBuildRequest): Observable<GlossaryBuildResponse> {
    return this.http.post<GlossaryBuildResponse>(`${this.apiUrl}/build`, request);
  }
}
