import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Volume, VolumeCreate } from '../models';

@Injectable({
  providedIn: 'root'
})
export class VolumeService {
  private apiUrl = 'api/volumes';

  constructor(private http: HttpClient) {}

  getByWorkId(workId: number): Observable<Volume[]> {
    return this.http.get<Volume[]>(`${this.apiUrl}?work_id=${workId}`);
  }

  getById(id: number): Observable<Volume> {
    return this.http.get<Volume>(`${this.apiUrl}/${id}`);
  }

  create(volume: VolumeCreate): Observable<Volume> {
    return this.http.post<Volume>(this.apiUrl, volume);
  }
}
