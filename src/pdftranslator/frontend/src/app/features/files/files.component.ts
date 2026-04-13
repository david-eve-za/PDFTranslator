import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

import { Subject, takeUntil } from 'rxjs';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { FileService, UploadProgress } from '../../core/services/file.service';
import { NotificationService } from '../../shared/services/notification.service';
import {
  FileUploadResponse,
  FileStatus,
  getFileStatusColor,
  getFileStatusIcon,
  formatFileSize,
} from '../../core/models/file.model';

type FileStatusType = 'pending' | 'processing' | 'done' | 'error';

@Component({
  selector: 'app-files',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './files.component.html',
  styleUrl: './files.component.scss',
  animations: [
    trigger('fileListAnimation', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(20px)' }),
          stagger('80ms', [
            animate('250ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
    trigger('uploadAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'scale(0.95)' }),
        animate('200ms ease-out', style({ opacity: 1, transform: 'scale(1)' })),
      ]),
      transition(':leave', [
        style({ opacity: 1, transform: 'scale(1)' }),
        animate('150ms ease-in', style({ opacity: 0, transform: 'scale(0.95)' })),
      ]),
    ]),
  ],
})
export class FilesComponent implements OnInit, OnDestroy {
  private fileService = inject(FileService);
  private notificationService = inject(NotificationService);
  private destroy$ = new Subject<void>();

  files: FileUploadResponse[] = [];
  isLoading = true;
  isUploading = false;
  uploadProgress: UploadProgress | null = null;

  currentPage = 1;
  pageSize = 20;
  totalFiles = 0;
  totalPages = 0;

  isDragOver = false;
  selectedFile: File | null = null;

  private dragCounter = 0;

  ngOnInit(): void {
    this.loadFiles();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadFiles(): void {
    this.isLoading = true;
    this.fileService.listFiles(this.currentPage, this.pageSize)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.files = response.items;
          this.totalFiles = response.total;
          this.totalPages = Math.ceil(response.total / this.pageSize);
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading files:', err);
          this.notificationService.error('Failed to load files');
          this.isLoading = false;
        },
      });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragCounter--;
    if (this.dragCounter === 0) {
      this.isDragOver = false;
    }
  }

  onDragEnter(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragCounter++;
    this.isDragOver = true;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    this.dragCounter = 0;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
      input.value = '';
    }
  }

  private uploadFile(file: File): void {
    if (!this.isValidFile(file)) {
      return;
    }

    this.isUploading = true;
    this.uploadProgress = null;

    this.fileService.uploadFile(file, {}, (progress) => {
      this.uploadProgress = progress;
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.isUploading = false;
          this.uploadProgress = null;
          this.notificationService.success(`File "${response.original_name}" uploaded successfully`);
          this.files.unshift(response);
          this.totalFiles++;
        },
        error: (err) => {
          this.isUploading = false;
          this.uploadProgress = null;
          console.error('Upload error:', err);
          this.notificationService.error(err.error?.detail || 'Failed to upload file');
        },
      });
  }

  private isValidFile(file: File): boolean {
    const validTypes = ['application/pdf', 'application/epub+zip'];
    const maxSize = 100 * 1024 * 1024;

    if (!validTypes.includes(file.type)) {
      this.notificationService.error('Only PDF and EPUB files are allowed');
      return false;
    }

    if (file.size > maxSize) {
      this.notificationService.error('File size must be less than 100MB');
      return false;
    }

    return true;
  }

  deleteFile(fileId: number, fileName: string): void {
    if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
      return;
    }

    this.fileService.deleteFile(fileId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.files = this.files.filter(f => f.id !== fileId);
          this.totalFiles--;
          this.notificationService.success(`File "${fileName}" deleted`);
        },
        error: (err) => {
          console.error('Delete error:', err);
          this.notificationService.error('Failed to delete file');
        },
      });
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadFiles();
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadFiles();
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadFiles();
    }
  }

  getStatusColor(status: string): string {
    return getFileStatusColor(status as FileStatusType);
  }

  getStatusIcon(status: string): string {
    return getFileStatusIcon(status as FileStatusType);
  }

  getPaginationPages(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
    const end = Math.min(this.totalPages, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }

  formatSize(bytes: number): string {
    return formatFileSize(bytes);
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
