import { Component, OnInit, inject, signal, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkService, WorkListResponse } from '../../core/services/work.service';
import { Work } from '../../core/models';

@Component({
  selector: 'app-work-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './work-selector.component.html',
  styleUrl: './work-selector.component.scss',
})
export class WorkSelectorComponent implements OnInit {
  private workService = inject(WorkService);

  works = signal<Work[]>([]);
  isLoading = signal(true);
  searchTerm = signal('');

  workSelected = output<Work>();

  filteredWorks = signal<Work[]>([]);

  ngOnInit(): void {
    this.loadWorks();
  }

  private loadWorks(): void {
    this.isLoading.set(true);
    this.workService.getAll().subscribe({
      next: (response: WorkListResponse) => {
        this.works.set(response.items);
        this.updateFiltered();
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
    this.updateFiltered();
  }

  private updateFiltered(): void {
    const term = this.searchTerm().toLowerCase().trim();
    const allWorks = this.works();
    if (!term) {
      this.filteredWorks.set(allWorks);
    } else {
      this.filteredWorks.set(
        allWorks.filter(w =>
          w.title.toLowerCase().includes(term) ||
          w.author.toLowerCase().includes(term)
        )
      );
    }
  }

  selectWork(work: Work): void {
    this.workSelected.emit(work);
  }

  getProgressPercentage(work: Work): number {
    return work.total_chapters > 0
      ? Math.round((work.translated_chapters / work.total_chapters) * 100)
      : 0;
  }
}
