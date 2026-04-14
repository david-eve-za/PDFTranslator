import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
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
  animations: [
    trigger('cardAnimation', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(20px)' }),
          stagger('100ms', [
            animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
  ],
})
export class LibraryComponent implements OnInit {
  private workService = inject(WorkService);
  private volumeService = inject(VolumeService);
  private ruleService = inject(SubstitutionRuleService);
  private router = inject(Router);

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
    this.errorMessage.set(null);

    this.volumeService.getByWorkId(work.id).subscribe({
      next: (response: VolumeListResponse) => {
        const volumes = response.items;
        if (volumes.length === 0) {
          this.errorMessage.set('No volumes found for this work');
          this.cleaningWorkId.set(null);
          return;
        }

        this.applyRulesToVolumes(work.title, volumes.map(v => v.id));
      },
      error: (err) => {
        this.errorMessage.set('Failed to load volumes');
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
            this.successMessage.set(`Applied rules to ${total} volume(s), ${totalModified} modification(s)`);
            setTimeout(() => this.successMessage.set(null), 5000);
          }
        },
        error: (err) => {
          processed++;
          console.error(`Error applying rules to volume ${volumeId}:`, err);

          if (processed === total) {
            this.cleaningWorkId.set(null);
            this.successMessage.set(`Applied rules to ${processed}/${total} volume(s)`);
            setTimeout(() => this.successMessage.set(null), 5000);
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
    const progress = this.getProgressPercentage(work);
    if (progress === 100) return 'complete';
    if (progress > 0) return 'in-progress';
    return 'not-started';
  }
}
