import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Work, WorkCreate, WorkUpdate } from '../models';

export interface WorkListResponse {
  items: Work[];
  total: number;
  page: number;
  page_size: number;
}

@Injectable({
  providedIn: 'root'
})
export class WorkService {
  private apiUrl = '/api/works';

  constructor(private http: HttpClient) {}

  getAll(page: number = 1, pageSize: number = 20): Observable<WorkListResponse> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<WorkListResponse>(this.apiUrl, { params });
  }

  getById(id: number): Observable<Work> {
    return this.http.get<Work>(`${this.apiUrl}/${id}`);
  }

  create(work: WorkCreate): Observable<Work> {
    return this.http.post<Work>(this.apiUrl, work);
  }

  update(id: number, work: WorkUpdate): Observable<Work> {
    return this.http.put<Work>(`${this.apiUrl}/${id}`, work);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
