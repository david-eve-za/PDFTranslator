import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Language {
  code: string;
  name: string;
}

export interface Provider {
  id: string;
  name: string;
  description: string;
}

@Injectable({
  providedIn: 'root'
})
export class TranslationConfigService {
  private apiUrl = 'api';

  constructor(private http: HttpClient) {}

  getLanguages(): Observable<Language[]> {
    return this.http.get<Language[]>(`${this.apiUrl}/languages`);
  }

  getProviders(): Observable<Provider[]> {
    return this.http.get<Provider[]>(`${this.apiUrl}/providers`);
  }
}
