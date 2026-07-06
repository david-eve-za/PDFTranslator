import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import {
  TranslationStartRequest,
  TranslationJobStatus,
  TranslationProgressEvent,
  TranslationJobListResponse,
} from '../models/translation-progress.model';

@Injectable({
  providedIn: 'root',
})
export class TranslationService {
  private apiUrl = '/api/translate';

  constructor(private http: HttpClient) {}

  startTranslation(request: TranslationStartRequest): Observable<{ job_id: number; status: string }> {
    return this.http.post<{ job_id: number; status: string }>(this.apiUrl, request);
  }

  getJobStatus(jobId: number): Observable<TranslationJobStatus> {
    return this.http.get<TranslationJobStatus>(`${this.apiUrl}/${jobId}`);
  }

  streamProgress(jobId: number): Observable<TranslationProgressEvent> {
    const subject = new Subject<TranslationProgressEvent>();
    const eventSource = new EventSource(`${this.apiUrl}/${jobId}/stream`);

    eventSource.addEventListener('progress', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      subject.next({ event_type: 'progress', ...data });
    });

    eventSource.addEventListener('chapter_complete', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      subject.next({ event_type: 'chapter_complete', ...data });
    });

    eventSource.addEventListener('job_complete', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      subject.next({ event_type: 'job_complete', ...data });
      eventSource.close();
      subject.complete();
    });

    // onerror fires for both connection errors AND dispatched 'error' events
    // We handle both by checking if we already processed an 'error' event
    let errorEmitted = false;

    eventSource.addEventListener('error', (event: MessageEvent) => {
      if (errorEmitted) return;
      let message = 'SSE connection error';
      try {
        const data = JSON.parse(event.data);
        message = data.message || message;
      } catch {
        // Use default message
      }
      errorEmitted = true;
      subject.next({ event_type: 'error', message });
      eventSource.close();
      subject.complete();
    });

    // Native onerror is a fallback - but we only use it if no 'error' event was dispatched
    eventSource.onerror = () => {
      // Browser fires onerror AFTER dispatching 'error' event in some cases
      // Use a small delay to allow the event listener to process first
      setTimeout(() => {
        if (!errorEmitted) {
          errorEmitted = true;
          subject.next({ event_type: 'error', message: 'SSE connection lost' });
          eventSource.close();
          subject.complete();
        }
      }, 0);
    };

    return subject.asObservable();
  }

  listJobs(): Observable<TranslationJobListResponse> {
    return this.http.get<TranslationJobListResponse>(this.apiUrl);
  }
}