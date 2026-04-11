import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { WorkService } from '../../core/services/work.service';
import { Work } from '../../core/models';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './library.component.html',
  styleUrl: './library.component.scss'
})
export class LibraryComponent implements OnInit {
  private workService = inject(WorkService);

  works: Work[] = [];
  isLoading = true;
  searchTerm = '';

  ngOnInit(): void {
    this.loadWorks();
  }

  private loadWorks(): void {
    this.isLoading = true;
    this.workService.getAll().subscribe({
      next: (works: Work[]) => {
        this.works = works;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading works:', err);
        this.isLoading = false;
      }
    });
  }

  get filteredWorks(): Work[] {
    if (!this.searchTerm) return this.works;
    const term = this.searchTerm.toLowerCase();
    return this.works.filter(w => 
      w.title.toLowerCase().includes(term) || 
      w.author.toLowerCase().includes(term)
    );
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
