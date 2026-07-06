import { Component, OnDestroy, OnInit, inject, signal, computed, input, output, model, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Volume, Chapter } from '../../../core/models';
import { VolumeService } from '../../../core/services/volume.service';
import { ChapterService } from '../../../core/services/chapter.service';
import { TranslationService } from '../../../core/services/translation.service';
import { Work } from '../../../core/models';
import { TranslationScope, TranslationStartRequest } from '../../../core/models/translation-progress.model';
import { Subscription } from 'rxjs';

export interface VolumeGroup {
  volumeId: number;
  volumeNumber: number;
  title: string;
  chapters: Chapter[];
}

@Component({
  selector: 'app-translation-comparison',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './translation-comparison.component.html',
  styleUrl: './translation-comparison.component.scss',
})
export class TranslationComparisonComponent implements OnInit, OnDestroy {
  private volumeService = inject(VolumeService);
  private chapterService = inject(ChapterService);
  private translationService = inject(TranslationService);

  // Inputs as signals for modern Angular
  work = input.required<Work>();
  selectedScope = input<TranslationScope | null>(null);
  selectedVolumeId = model<number | null>(null);
  selectedChapterId = model<number | null>(null);

  // Outputs
  volumeSelected = output<number | null>();
  chapterSelected = output<number | null>();
  retranslateRequested = output<{ chapterId: number; volumeId: number }>();

  private messageTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private subscriptions: Subscription[] = [];

  // Internal state
  volumes = signal<Volume[]>([]);
  chapters = signal<Chapter[]>([]);
  expandedVolumes = signal<Set<number>>(new Set());
  selectedChapter = signal<Chapter | null>(null);
  isLoadingVolumes = signal(false);
  isRetranslating = signal(false);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  volumeGroups = computed<VolumeGroup[]>(() => {
    const vols = this.volumes();
    const chaps = this.chapters();
    const chapterMap = new Map<number, Chapter[]>();
    for (const c of chaps) {
      if (!chapterMap.has(c.volume_id)) {
        chapterMap.set(c.volume_id, []);
      }
      chapterMap.get(c.volume_id)!.push(c);
    }

    return vols
      .sort((a, b) => a.volume_number - b.volume_number)
      .map(v => ({
        volumeId: v.id,
        volumeNumber: v.volume_number,
        title: `Volume ${v.volume_number}`,
        chapters: (chapterMap.get(v.id) || []).sort((a, b) => a.chapter_number - b.chapter_number),
      }));
  });

  totalChapters = computed(() => this.chapters().length);
  translatedChapters = computed(() => this.chapters().filter(c => c.is_translated).length);
  pendingChapters = computed(() => this.totalChapters() - this.translatedChapters());

  // ViewChild references for synchronized scrolling
  @ViewChild('originalTextarea') originalTextarea!: ElementRef<HTMLTextAreaElement>;
  @ViewChild('translatedTextarea') translatedTextarea!: ElementRef<HTMLTextAreaElement>;

  private isSyncing = false;

  ngOnInit(): void {
    this.loadVolumes();
  }

  ngOnDestroy(): void {
    this.clearMessageTimeout();
    this.subscriptions.forEach(s => s.unsubscribe());
  }

  private loadVolumes(): void {
    this.isLoadingVolumes.set(true);
    this.errorMessage.set(null);

    const sub = this.volumeService.getByWorkId(this.work().id).subscribe({
      next: (response) => {
        this.volumes.set(response.items);
        this.isLoadingVolumes.set(false);
        this.expandAllVolumes();
        // Load chapters for all volumes
        this.loadAllChapters();
      },
      error: (err) => {
        this.isLoadingVolumes.set(false);
        this.showError('Failed to load volumes: ' + (err.message || 'Unknown error'));
      },
    });
    this.subscriptions.push(sub);
  }

  private loadAllChapters(): void {
    const volumeIds = this.volumes().map(v => v.id);
    for (const volumeId of volumeIds) {
      this.loadChaptersForVolume(volumeId);
    }
  }

  private expandAllVolumes(): void {
    const ids = new Set(this.volumes().map(v => v.id));
    this.expandedVolumes.set(ids);
  }

  onVolumeChange(volumeId: number | null): void {
    this.selectedVolumeId.set(volumeId);
    this.volumeSelected.emit(volumeId);
    this.selectedChapter.set(null);
    this.chapterSelected.emit(null);
    // No need to load chapters - they're already loaded for all volumes
  }

  private loadChaptersForVolume(volumeId: number): void {
    this.isLoadingVolumes.set(true);

    const sub = this.chapterService.getByVolume(volumeId).subscribe({
      next: (response) => {
        // Merge chapters for this volume with existing chapters
        this.chapters.update(existing => {
          const otherChapters = existing.filter(c => c.volume_id !== volumeId);
          return [...otherChapters, ...response.items];
        });
        this.isLoadingVolumes.set(false);
        // Auto-expand this volume
        this.expandedVolumes.update(set => {
          const next = new Set(set);
          next.add(volumeId);
          return next;
        });
      },
      error: (err) => {
        this.isLoadingVolumes.set(false);
        this.showError('Failed to load chapters: ' + (err.message || 'Unknown error'));
      },
    });
    this.subscriptions.push(sub);
  }

  toggleVolume(volumeId: number): void {
    this.expandedVolumes.update(set => {
      const next = new Set(set);
      if (next.has(volumeId)) {
        next.delete(volumeId);
      } else {
        next.add(volumeId);
      }
      return next;
    });
  }

  isVolumeExpanded(volumeId: number): boolean {
    return this.expandedVolumes().has(volumeId);
  }

  expandAll(): void {
    const ids = new Set(this.volumes().map(v => v.id));
    this.expandedVolumes.set(ids);
  }

  collapseAll(): void {
    this.expandedVolumes.set(new Set());
  }

  hasVolumes(): boolean {
    return this.volumes().length > 0;
  }

  onChapterClick(chapter: Chapter): void {
    this.selectedChapter.set(chapter);
    this.chapterSelected.emit(chapter.id);
  }

  closeChapterDetail(): void {
    this.selectedChapter.set(null);
    this.chapterSelected.emit(null);
  }

  // Synchronized scrolling for textareas
  onScrollSync(source: 'original' | 'translated', event: Event): void {
    if (this.isSyncing) return;
    
    const sourceEl = event.target as HTMLTextAreaElement;
    const targetEl = source === 'original' 
      ? this.translatedTextarea?.nativeElement 
      : this.originalTextarea?.nativeElement;
    
    if (targetEl) {
      this.isSyncing = true;
      targetEl.scrollTop = sourceEl.scrollTop;
      targetEl.scrollLeft = sourceEl.scrollLeft;
      // Use requestAnimationFrame to ensure sync is complete
      requestAnimationFrame(() => {
        this.isSyncing = false;
      });
    }
  }

  retranslateChapter(chapter: Chapter, event: Event): void {
    event.stopPropagation();
    if (!chapter.id || !chapter.volume_id) return;

    this.isRetranslating.set(true);
    this.retranslateRequested.emit({ chapterId: chapter.id, volumeId: chapter.volume_id });
  }

  copyTranslation(chapter: Chapter): void {
    if (!chapter.translated_text) return;

    navigator.clipboard.writeText(chapter.translated_text).then(() => {
      this.showSuccess('Translation copied to clipboard');
    }).catch(() => {
      this.showError('Failed to copy translation');
    });
  }

  getTranslationStatus(chapter: Chapter): 'translated' | 'pending' | 'partial' {
    if (!chapter.original_text) return 'pending';
    if (chapter.is_translated && chapter.translated_text && chapter.translated_text.length > 0) {
      return 'translated';
    }
    if (chapter.translated_text && chapter.translated_text.length > 0) {
      return 'partial';
    }
    return 'pending';
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'translated': return '✓';
      case 'partial': return '◐';
      default: return '○';
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'translated': return 'status-translated';
      case 'partial': return 'status-partial';
      default: return 'status-pending';
    }
  }

  formatTextPreview(text: string | undefined, maxLength: number = 200): string {
    if (!text) return 'No text available';
    const cleaned = text.replace(/\s+/g, ' ').trim();
    return cleaned.length > maxLength ? cleaned.substring(0, maxLength) + '...' : cleaned;
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

  // Called by parent when re-translation is complete
  onRetranslateComplete(event: { success: boolean; chapterId: number; volumeId: number }): void {
    this.isRetranslating.set(false);
    if (event.success) {
      this.showSuccess('Chapter re-translated successfully');
      // Reload the chapters for this volume to get updated translation
      this.loadChaptersForVolume(event.volumeId);
    } else {
      this.showError('Failed to re-translate chapter');
    }
  }
}