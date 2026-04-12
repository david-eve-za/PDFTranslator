import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpParams } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';
import {
  FileUploadResponse,
  FileListResponse,
  FileUploadQuery,
  FileDeleteResponse,
} from '../models/file.model';

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

@Injectable({
  providedIn: 'root',
})
export class FileService {
  private http = inject(HttpClient);
  private apiUrl = '/api/files';

  uploadFile(
    file: File,
    query: FileUploadQuery = {},
    progressCallback?: (progress: UploadProgress) => void
  ): Observable<FileUploadResponse> {
    let params = new HttpParams();
    if (query.source_lang) {
      params = params.set('source_lang', query.source_lang);
    }
    if (query.target_lang) {
      params = params.set('target_lang', query.target_lang);
    }

    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<FileUploadResponse>(this.apiUrl + '/upload', formData, {
      params,
      reportProgress: true,
      observe: 'events',
    }).pipe(
      tap((event: HttpEvent<FileUploadResponse>) => {
        if (progressCallback && event.type === HttpEventType.UploadProgress) {
          const progress: UploadProgress = {
            loaded: event.loaded,
            total: event.total || 0,
            percentage: event.total
              ? Math.round((event.loaded / event.total) * 100)
              : 0,
          };
          progressCallback(progress);
        }
      }),
      map((event: HttpEvent<FileUploadResponse>) => {
        if (event.type === HttpEventType.Response) {
          return event.body as FileUploadResponse;
        }
        return {
          id: 0,
          filename: file.name,
          original_name: file.name,
          file_size: file.size,
          file_type: file.type,
          work_id: null,
          work_title: null,
          volume_id: null,
          volume_number: null,
          status: 'pending',
          created_at: new Date().toISOString(),
        };
      })
    );
  }

  listFiles(
    page: number = 1,
    pageSize: number = 20
  ): Observable<FileListResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());

    return this.http.get<FileListResponse>(this.apiUrl, { params });
  }

  getFile(fileId: number): Observable<FileUploadResponse> {
    return this.http.get<FileUploadResponse>(`${this.apiUrl}/${fileId}`);
  }

  deleteFile(fileId: number): Observable<FileDeleteResponse> {
    return this.http.delete<FileDeleteResponse>(`${this.apiUrl}/${fileId}`);
  }
}
