import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { WorkService } from '../../core/services/work.service';
import { GlossaryService } from '../../core/services/glossary.service';
import { RecentActivity, Work, GlossaryTerm } from '../../core/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private workService = inject(WorkService);
  private glossaryService = inject(GlossaryService);

  stats = {
    totalWorks: 0,
    totalGlossaryTerms: 0,
    translationsThisWeek: 5,
    averageProgress: 0
  };

  recentActivities: RecentActivity[] = [];
  isLoading = true;

  ngOnInit(): void {
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.isLoading = true;

    this.workService.getAll().subscribe({
      next: (works: Work[]) => {
        this.stats.totalWorks = works.length;
        const totalProgress = works.reduce((sum, w) => 
          sum + (w.total_chapters > 0 ? (w.translated_chapters / w.total_chapters) * 100 : 0), 0
        );
        this.stats.averageProgress = works.length > 0 ? Math.round(totalProgress / works.length) : 0;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading works:', err);
        this.isLoading = false;
      }
    });

    this.glossaryService.getAll().subscribe({
      next: (terms: GlossaryTerm[]) => {
        this.stats.totalGlossaryTerms = terms.length;
      },
      error: (err) => console.error('Error loading glossary:', err)
    });

    this.dashboardService.getRecentActivities().subscribe({
      next: (activities: RecentActivity[]) => {
        this.recentActivities = activities;
      },
      error: (err) => console.error('Error loading activities:', err)
    });
  }

  getActivityIcon(type: string): string {
    const icons: Record<string, string> = {
      translation: '🌐',
      glossary: '📖',
      import: '📥',
      split: '✂️'
    };
    return icons[type] || '📝';
  }

  formatTime(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  }
}
