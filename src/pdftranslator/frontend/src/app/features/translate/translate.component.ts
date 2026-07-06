import { Component, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { WorkService } from '../../core/services/work.service';
import { TranslationService } from '../../core/services/translation.service';
import { ThemeService } from '../../core/services/theme.service';
import { Work } from '../../core/models';
import { TranslationScope, TranslationStartRequest, TranslationProgressEvent } from '../../core/models/translation-progress.model';
import { WorkSelectorComponent } from './components/work-selector.component';
import { ScopeSelectorComponent } from './components/scope-selector.component';
import { TranslateConfigComponent } from './components/translate-config.component';
import { TranslateProgressComponent } from './components/translate-progress.component';
import { TranslateSummaryComponent } from './components/translate-summary.component';

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    WorkSelectorComponent,
    ScopeSelectorComponent,
    TranslateConfigComponent,
    TranslateProgressComponent,
    TranslateSummaryComponent,
  ],
  templateUrl: './translate.component.html',
  styleUrl: './translate.component.scss',
})
export class TranslateComponent implements OnDestroy {
  private workService = inject(WorkService);
  private translationService = inject(TranslationService);
  private themeService = inject(ThemeService);

  private messageTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private progressSubscription: Subscription | null = null;

  currentStep = signal(1);
  selectedWork = signal<Work | null>(null);
  selectedScope = signal<TranslationScope | null>(null);
  selectedVolumeId = signal<number | null>(null);
  selectedChapterId = signal<number | null>(null);
  skipTranslated = signal(true);
  dryRun = signal(false);
  jobId = signal<number | null>(null);
  progressData = signal<TranslationProgressEvent | null>(null);

  // Use Map keyed by chapter_id for uniqueness
  chapterStatuses = signal<Map<number, { title: string; status: string }>>(new Map());
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);
  isTranslating = signal(false);

  summarySuccess = signal(0);
  summaryFailure = signal(0);
  summarySkipped = signal(0);

  ngOnDestroy(): void {
    this.clearMessageTimeout();
    if (this.progressSubscription) {
      this.progressSubscription.unsubscribe();
    }
  }

  private clearMessageTimeout(): void {
    if (this.messageTimeoutId) {
      clearTimeout(this.messageTimeoutId);
      this.messageTimeoutId = null;
    }
  }

  private showSuccess(message: string, duration: number = 3000): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(message);
    this.messageTimeoutId = setTimeout(() => {
      this.successMessage.set(null);
      this.messageTimeoutId = null;
    }, duration);
  }

  private showError(message: string): void {
    this.clearMessageTimeout();
    this.successMessage.set(null);
    this.errorMessage.set(message);
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  get currentTheme() {
    return this.themeService.currentTheme();
  }

  onWorkSelected(work: Work): void {
    this.selectedWork.set(work);
    this.currentStep.set(2);
    this.clearMessages();
  }

  onScopeSelected(scope: TranslationScope): void {
    this.selectedScope.set(scope);
    this.currentStep.set(3);
    this.clearMessages();
  }

  onVolumeSelected(volumeId: number | null): void {
    this.selectedVolumeId.set(volumeId);
  }

  onChapterSelected(chapterId: number | null): void {
    this.selectedChapterId.set(chapterId);
  }

  onConfigChanged(config: { skip_translated: boolean; dry_run: boolean }): void {
    this.skipTranslated.set(config.skip_translated);
    this.dryRun.set(config.dry_run);
  }

  canStartTranslation(): boolean {
    const scope = this.selectedScope();
    if (!scope) return false;
    if (scope === 'all_volume' && this.selectedVolumeId() === null) return false;
    if (scope === 'single_chapter' && this.selectedChapterId() === null) return false;
    return true;
  }

  // Validation for config step - always valid, just show warnings if needed
  getConfigWarnings(): string[] {
    const warnings: string[] = [];
    if (this.dryRun()) {
      warnings.push('Dry run mode: No changes will be saved to the database');
    }
    if (!this.skipTranslated()) {
      warnings.push('Re-translating existing chapters will overwrite previous translations');
    }
    return warnings;
  }

  startTranslation(): void {
    const work = this.selectedWork();
    const scope = this.selectedScope();
    if (!work || !scope || !this.canStartTranslation()) return;

    this.isTranslating.set(true);
    this.clearMessages();
    this.chapterStatuses.set(new Map());
    this.progressData.set(null);
    this.currentStep.set(4);

    const request: TranslationStartRequest = {
      work_id: work.id,
      scope,
      volume_id: this.selectedVolumeId() ?? undefined,
      chapter_id: this.selectedChapterId() ?? undefined,
      source_lang: work.source_lang || 'en',
      target_lang: work.target_lang || 'es',
      skip_translated: this.skipTranslated(),
      dry_run: this.dryRun(),
    };

    this.translationService.startTranslation(request).subscribe({
      next: (response) => {
        this.jobId.set(response.job_id);
        this.connectToSSE(response.job_id);
      },
      error: (err) => {
        this.showError('Failed to start translation: ' + (err.message || 'Unknown error'));
        this.isTranslating.set(false);
      },
    });
  }

  private connectToSSE(jobId: number): void {
    if (this.progressSubscription) {
      this.progressSubscription.unsubscribe();
    }

    this.progressSubscription = this.translationService.streamProgress(jobId).subscribe({
      next: (event: TranslationProgressEvent) => {
        this.progressData.set(event);

        if (event.event_type === 'chapter_complete' && event.title && event.chapter_id) {
          const statuses = new Map(this.chapterStatuses());
          statuses.set(event.chapter_id, { title: event.title, status: event.chapter_status || 'success' });
          this.chapterStatuses.set(statuses);
        }

        if (event.event_type === 'job_complete') {
          this.isTranslating.set(false);
          this.summarySuccess.set(event.success_count ?? 0);
          this.summaryFailure.set(event.failure_count ?? 0);
          const statuses = this.chapterStatuses();
          const skipped = Array.from(statuses.values()).filter(s => s.status === 'skipped').length;
          this.summarySkipped.set(skipped);
          this.currentStep.set(5);
          this.showSuccess('Translation completed!');
        }

        if (event.event_type === 'error') {
          this.isTranslating.set(false);
          this.showError(event.message || 'Translation failed');
        }
      },
      error: () => {
        this.isTranslating.set(false);
        this.showError('SSE connection error. Check job status and try again.');
      },
    });
  }

  resetWizard(): void {
    this.currentStep.set(1);
    this.selectedWork.set(null);
    this.selectedScope.set(null);
    this.selectedVolumeId.set(null);
    this.selectedChapterId.set(null);
    this.skipTranslated.set(true);
    this.dryRun.set(false);
    this.jobId.set(null);
    this.progressData.set(null);
    this.chapterStatuses.set(new Map());
    this.isTranslating.set(false);
    this.summarySuccess.set(0);
    this.summaryFailure.set(0);
    this.summarySkipped.set(0);
    this.clearMessages();
  }

  goBack(): void {
    const step = this.currentStep();
    if (step > 1 && step < 5) {
      this.currentStep.set(step - 1);
    }
  }

  private clearMessages(): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  // Helper for template to iterate Map
  getChapterStatusEntries(): Array<[number, { title: string; status: string }]> {
    return Array.from(this.chapterStatuses().entries());
  }
}