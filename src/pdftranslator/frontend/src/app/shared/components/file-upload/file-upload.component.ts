import { Component, Output, EventEmitter, signal, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.scss'],
})
export class FileUploadComponent {
  @Output() fileSelected = new EventEmitter<File>();
  @ViewChild('fileInput') fileInputRef!: ElementRef<HTMLInputElement>;

  isDragging = signal(false);
  selectedFile = signal<File | null>(null);
  errorMessage = signal<string | null>(null);

  private readonly ALLOWED_EXTENSIONS = ['.pdf', '.epub'];
  private readonly MAX_FILE_SIZE = 50 * 1024 * 1024;

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  private handleFile(file: File): void {
    this.errorMessage.set(null);

    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!this.ALLOWED_EXTENSIONS.includes(extension)) {
      this.errorMessage.set(
        `Invalid file type. Allowed: ${this.ALLOWED_EXTENSIONS.join(', ')}`
      );
      return;
    }

    if (file.size > this.MAX_FILE_SIZE) {
      this.errorMessage.set(
        `File too large. Maximum size: ${this.MAX_FILE_SIZE / 1024 / 1024}MB`
      );
      return;
    }

    this.selectedFile.set(file);
    this.fileSelected.emit(file);
  }

  clearFile(): void {
    this.selectedFile.set(null);
    this.errorMessage.set(null);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i)) + ' ' + sizes[i];
  }
}
