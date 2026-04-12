import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Volume, VolumeCreate } from '../models';

export interface VolumeListResponse {
  items: Volume[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class VolumeService {
  private apiUrl = '/api/volumes';

  constructor(private http: HttpClient) {}

  getByWorkId(workId: number): Observable<VolumeListResponse> {
    const params = new HttpParams().set('work_id', workId.toString());
    return this.http.get<VolumeListResponse>(this.apiUrl, { params });
  }

  getById(id: number): Observable<Volume> {
    return this.http.get<Volume>(`${this.apiUrl}/${id}`);
  }

  create(volume: VolumeCreate): Observable<Volume> {
    return this.http.post<Volume>(this.apiUrl, volume);
  }
}
