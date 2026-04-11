import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GlossaryTerm, GlossaryTermCreate, GlossaryTermUpdate, EntityType } from '../models';

@Injectable({
  providedIn: 'root'
})
export class GlossaryService {
  private apiUrl = 'api/glossaryTerms';

  constructor(private http: HttpClient) {}

  getAll(workId?: number, entityType?: EntityType): Observable<GlossaryTerm[]> {
    let params = new HttpParams();
    if (workId) params = params.set('work_id', workId.toString());
    if (entityType) params = params.set('entity_type', entityType);
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
}
