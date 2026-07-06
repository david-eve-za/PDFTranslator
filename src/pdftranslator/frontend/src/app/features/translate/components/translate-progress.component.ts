import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslationProgressEvent } from '../../../core/models/translation-progress.model';

@Component({
  selector: 'app-translate-progress',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './translate-progress.component.html',
  styleUrl: './translate-progress.component.scss',
})
export class TranslateProgressComponent {
  progressData = input<TranslationProgressEvent | null>(null);
  // Map<chapter_id, { title: string; status: string }>
  chapterStatuses = input<Map<number, { title: string; status: string }>>(new Map());

  get progressPercentage(): number {
    const data = this.progressData();
    if (!data || !data.total_chapters || data.completed_chapters === undefined) return 0;
    return Math.round((data.completed_chapters / data.total_chapters) * 100);
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'success': return '✓';
      case 'failure': return '✗';
      case 'skipped': return '○';
      case 'translating': return '⟳';
      default: return '○';
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'success': return 'status-success';
      case 'failure': return 'status-failure';
      case 'skipped': return 'status-skipped';
      case 'translating': return 'status-translating';
      default: return 'status-pending';
    }
  }

  // Template helpers
  getChapterEntries(): Array<[number, { title: string; status: string }]> {
    return Array.from(this.chapterStatuses().entries());
  }
}