import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { DashboardService } from '../../core/services/dashboard.service';
import { WorkService, WorkListResponse } from '../../core/services/work.service';
import { GlossaryService } from '../../core/services/glossary.service';
import { RecentActivity, Work, GlossaryTerm } from '../../core/models';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, BaseChartDirective, SkeletonLoaderComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
  animations: [
    trigger('statsAnimation', [
      transition(':enter', [
        query('.stats-card', [
          style({ opacity: 0, transform: 'scale(0.9)' }),
          stagger('100ms', [
            animate('300ms ease-out', style({ opacity: 1, transform: 'scale(1)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
  ],
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

  // Chart data
  translationChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: ['Completed', 'In Progress', 'Pending'],
    datasets: [{
      data: [0, 0, 0],
      backgroundColor: ['#10b981', '#f59e0b', '#94a3b8'],
      borderWidth: 0
    }]
  };

  translationChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          pointStyle: 'circle'
        }
      }
    },
    cutout: '65%'
  };

  ngOnInit(): void {
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.isLoading = true;

    this.workService.getAll().subscribe({
      next: (response: WorkListResponse) => {
        const works = response.items;
        this.stats.totalWorks = works.length;
        const totalProgress = works.reduce((sum, w) =>
          sum + (w.total_chapters > 0 ? (w.translated_chapters / w.total_chapters) * 100 : 0), 0
        );
        this.stats.averageProgress = works.length > 0 ? Math.round(totalProgress / works.length) : 0;

        // Calculate chart data
        let completed = 0;
        let inProgress = 0;
        let pending = 0;

        works.forEach(work => {
          const progress = work.total_chapters > 0
            ? (work.translated_chapters / work.total_chapters) * 100
            : 0;
          if (progress === 100) completed++;
          else if (progress > 0) inProgress++;
          else pending++;
        });

        this.translationChartData.datasets[0].data = [completed, inProgress, pending];

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
