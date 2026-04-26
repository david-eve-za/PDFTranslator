import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Chapter } from '../models';

export interface ChapterListResponse {
  items: Chapter[];
  total: number;
}

@Injectable({
  providedIn: 'root',
})
export class ChapterService {
  private apiUrl = '/api/chapters';

  constructor(private http: HttpClient) {}

  getByVolume(volumeId: number): Observable<ChapterListResponse> {
    const params = new HttpParams().set('volume_id', volumeId.toString());
    return this.http.get<ChapterListResponse>(this.apiUrl, { params });
  }

  getById(id: number): Observable<Chapter> {
    return this.http.get<Chapter>(`${this.apiUrl}/${id}`);
  }
}
