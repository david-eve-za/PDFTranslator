import { Component, OnInit, OnDestroy, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { WorkService, WorkListResponse } from '../../core/services/work.service';
import { VolumeService, VolumeListResponse } from '../../core/services/volume.service';
import { SubstitutionRuleService } from '../../core/services/substitution-rule.service';
import { Work } from '../../core/models';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './library.component.html',
  styleUrl: './library.component.scss',
})
export class LibraryComponent implements OnInit, OnDestroy {
  private workService = inject(WorkService);
  private volumeService = inject(VolumeService);
  private ruleService = inject(SubstitutionRuleService);
  private router = inject(Router);

  private messageTimeoutId: ReturnType<typeof setTimeout> | null = null;

  works = signal<Work[]>([]);
  isLoading = signal(true);
  searchTerm = signal('');
  cleaningWorkId = signal<number | null>(null);
  successMessage = signal<string | null>(null);
  errorMessage = signal<string | null>(null);

  filteredWorks = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const allWorks = this.works();
    if (!term) return allWorks;
    return allWorks.filter(w =>
      w.title.toLowerCase().includes(term) ||
      w.author.toLowerCase().includes(term)
    );
  });

  ngOnInit(): void {
    this.loadWorks();
  }

  ngOnDestroy(): void {
    this.clearMessageTimeout();
  }

  private clearMessageTimeout(): void {
    if (this.messageTimeoutId) {
      clearTimeout(this.messageTimeoutId);
      this.messageTimeoutId = null;
    }
  }

  private showSuccess(message: string, duration: number = 5000): void {
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

  private clearMessages(): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  private loadWorks(): void {
    this.isLoading.set(true);
    this.workService.getAll().subscribe({
      next: (response: WorkListResponse) => {
        this.works.set(response.items);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Error loading works:', err);
        this.isLoading.set(false);
      }
    });
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
  }

  onSplit(workId: number): void {
    this.router.navigate(['/split'], { queryParams: { workId } });
  }

  onClean(work: Work): void {
    if (!confirm(`Apply substitution rules to all volumes of "${work.title}"?`)) {
      return;
    }

    this.cleaningWorkId.set(work.id);
    this.clearMessages();

    this.volumeService.getByWorkId(work.id).subscribe({
      next: (response: VolumeListResponse) => {
        const volumes = response.items;
        if (volumes.length === 0) {
          this.showError('No volumes found for this work');
          this.cleaningWorkId.set(null);
          return;
        }

        this.applyRulesToVolumes(work.title, volumes.map(v => v.id));
      },
      error: (err) => {
        this.showError('Failed to load volumes');
        this.cleaningWorkId.set(null);
        console.error('Error loading volumes:', err);
      }
    });
  }

  private applyRulesToVolumes(workTitle: string, volumeIds: number[]): void {
    let processed = 0;
    let totalModified = 0;
    const total = volumeIds.length;

    for (const volumeId of volumeIds) {
      this.ruleService.applyToVolume(volumeId).subscribe({
        next: (result) => {
          processed++;
          totalModified += result.modified_count || 0;

          if (processed === total) {
            this.cleaningWorkId.set(null);
            this.showSuccess(`Applied rules to ${total} volume(s), ${totalModified} modification(s)`);
          }
        },
        error: (err) => {
          processed++;
          console.error(`Error applying rules to volume ${volumeId}:`, err);

          if (processed === total) {
            this.cleaningWorkId.set(null);
            this.showSuccess(`Applied rules to ${processed}/${total} volume(s)`);
          }
        }
      });
    }
  }

  isCleaning(workId: number): boolean {
    return this.cleaningWorkId() === workId;
  }

  getProgressPercentage(work: Work): number {
    return work.total_chapters > 0
      ? Math.round((work.translated_chapters / work.total_chapters) * 100)
      : 0;
  }

  getProgressClass(work: Work): string {
    const percentage = this.getProgressPercentage(work);
    if (percentage >= 100) return 'complete';
    if (percentage > 0) return 'in-progress';
    return 'not-started';
  }
}
