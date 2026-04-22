import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ProgressStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

@Component({
  selector: 'app-progress-indicator',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './progress-indicator.component.html',
  styleUrl: './progress-indicator.component.scss',
})
export class ProgressIndicatorComponent {
  progress = input(0);
  status = input<ProgressStatus>('idle');
  message = input<string | null>(null);

  get statusIcon(): string {
    switch (this.status()) {
      case 'uploading':
      case 'processing':
        return 'loading';
      case 'completed':
        return 'success';
      case 'error':
        return 'error';
      default:
        return 'idle';
    }
  }

  get statusText(): string {
    if (this.message()) {
      return this.message()!;
    }

    switch (this.status()) {
      case 'uploading':
        return `Uploading... ${this.progress()}%`;
      case 'processing':
        return `Processing... ${this.progress()}%`;
      case 'completed':
        return 'Completed successfully!';
      case 'error':
        return 'An error occurred';
      default:
        return 'Ready';
    }
  }

  get progressColor(): string {
    if (this.status() === 'error') {
      return 'var(--color-error)';
    }
    if (this.status() === 'completed') {
      return 'var(--color-success)';
    }
    return 'var(--color-primary)';
  }
}
