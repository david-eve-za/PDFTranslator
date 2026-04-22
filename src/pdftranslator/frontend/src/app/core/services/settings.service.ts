import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Settings, SettingsUpdateRequest } from '../models';

@Injectable({
  providedIn: 'root',
})
export class SettingsService {
  private apiUrl = '/api/settings';

  constructor(private http: HttpClient) {}

  getSettings(): Observable<Settings> {
    return this.http.get<Settings>(this.apiUrl);
  }

  updateSettings(settings: SettingsUpdateRequest): Observable<{ message: string; restart_required: boolean }> {
    return this.http.put<{ message: string; restart_required: boolean }>(this.apiUrl, settings);
  }

  requestRestart(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/restart`, {});
  }
}
