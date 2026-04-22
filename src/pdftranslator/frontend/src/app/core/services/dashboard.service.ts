import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RecentActivity } from '../models';

export interface DashboardStats {
  total_works: number;
  total_glossary_terms: number;
  translations_this_week: number;
  average_progress: number;
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private apiUrl = 'api';

  constructor(private http: HttpClient) {}

  getRecentActivities(): Observable<RecentActivity[]> {
    return this.http.get<RecentActivity[]>(`${this.apiUrl}/recentActivities`);
  }
}
