import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Work, WorkCreate, WorkUpdate } from '../models';

@Injectable({
  providedIn: 'root'
})
export class WorkService {
  private apiUrl = 'api/works';

  constructor(private http: HttpClient) {}

  getAll(): Observable<Work[]> {
    return this.http.get<Work[]>(this.apiUrl);
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
