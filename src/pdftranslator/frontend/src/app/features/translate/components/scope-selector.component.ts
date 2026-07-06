import { Component, OnInit, inject, signal, output, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Work } from '../../../core/models';
import { VolumeService, VolumeListResponse } from '../../../core/services/volume.service';
import { ChapterService, ChapterListResponse } from '../../../core/services/chapter.service';
import { Volume } from '../../../core/models/volume.model';
import { Chapter } from '../../../core/models/chapter.model';
import { TranslationScope } from '../../../core/models/translation-progress.model';

@Component({
  selector: 'app-scope-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scope-selector.component.html',
  styleUrl: './scope-selector.component.scss',
})
export class ScopeSelectorComponent implements OnInit {
  work = input.required<Work>();

  private volumeService = inject(VolumeService);
  private chapterService = inject(ChapterService);

  selectedScope = signal<TranslationScope | null>(null);
  volumes = signal<Volume[]>([]);
  chapters = signal<Chapter[]>([]);
  selectedVolumeId = signal<number | null>(null);
  selectedChapterId = signal<number | null>(null);

  scopeSelected = output<TranslationScope>();
  volumeSelected = output<number | null>();
  chapterSelected = output<number | null>();

  ngOnInit(): void {
    this.loadVolumes();
  }

  private loadVolumes(): void {
    const workId = this.work().id;
    if (!workId) return;
    this.volumeService.getByWorkId(workId).subscribe({
      next: (response: VolumeListResponse) => {
        this.volumes.set(response.items);
      },
    });
  }

  selectScope(scope: TranslationScope): void {
    this.selectedScope.set(scope);
    this.scopeSelected.emit(scope);
    if (scope !== 'all_book') {
      this.selectedVolumeId.set(null);
      this.selectedChapterId.set(null);
      this.chapters.set([]);
      this.volumeSelected.emit(null);
      this.chapterSelected.emit(null);
    }
  }

  onVolumeChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const volumeId = Number(select.value);
    this.selectedVolumeId.set(volumeId);
    this.volumeSelected.emit(volumeId);
    this.selectedChapterId.set(null);
    this.chapterSelected.emit(null);
    this.chapterService.getByVolume(volumeId).subscribe({
      next: (response: ChapterListResponse) => {
        this.chapters.set(response.items);
      },
    });
  }

  onChapterChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const chapterId = Number(select.value);
    this.selectedChapterId.set(chapterId);
    this.chapterSelected.emit(chapterId);
  }
}
