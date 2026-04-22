import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ParsedBlock {
  block_type: string;
  title: string | null;
  content: string;
  start_line: number;
  end_line: number;
}

export interface SplitPreviewRequest {
  text: string;
}

export interface SplitPreviewResponse {
  blocks: ParsedBlock[];
  has_errors: boolean;
  error_message: string | null;
}

export interface SplitProcessRequest {
  volume_id: number;
  text: string;
}

export interface SplitProcessResponse {
  success: boolean;
  chapters_created: number;
  blocks: ParsedBlock[];
  error_message: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class SplitService {
  private apiUrl = '/api/split';

  constructor(private http: HttpClient) {}

  preview(text: string): Observable<SplitPreviewResponse> {
    return this.http.post<SplitPreviewResponse>(`${this.apiUrl}/preview`, { text });
  }

  process(volumeId: number, text: string): Observable<SplitProcessResponse> {
    return this.http.post<SplitProcessResponse>(`${this.apiUrl}/process`, {
      volume_id: volumeId,
      text
    });
  }
}
