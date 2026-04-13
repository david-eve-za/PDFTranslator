import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  SubstitutionRule,
  SubstitutionRuleCreate,
  SubstitutionRuleUpdate,
  ApplyRulesRequest,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class SubstitutionRuleService {
  private apiUrl = '/api/substitution-rules';

  constructor(private http: HttpClient) {}

  getAll(activeOnly: boolean = false): Observable<SubstitutionRule[]> {
    const params = new HttpParams().set('active_only', activeOnly.toString());
    return this.http.get<SubstitutionRule[]>(this.apiUrl, { params });
  }

  getById(id: number): Observable<SubstitutionRule> {
    return this.http.get<SubstitutionRule>(`${this.apiUrl}/${id}`);
  }

  create(rule: SubstitutionRuleCreate): Observable<SubstitutionRule> {
    return this.http.post<SubstitutionRule>(this.apiUrl, rule);
  }

  update(id: number, rule: SubstitutionRuleUpdate): Observable<SubstitutionRule> {
    return this.http.put<SubstitutionRule>(`${this.apiUrl}/${id}`, rule);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  applyToVolume(volumeId: number, request?: ApplyRulesRequest): Observable<{ success: boolean; modified_count: number }> {
    return this.http.post<{ success: boolean; modified_count: number }>(
      `${this.apiUrl}/apply/${volumeId}`,
      request
    );
  }
}
