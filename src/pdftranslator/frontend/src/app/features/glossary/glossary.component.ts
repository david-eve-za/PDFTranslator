import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { GlossaryService } from '../../core/services/glossary.service';
import { WorkService, WorkListResponse } from '../../core/services/work.service';
import { TranslationConfigService } from '../../core/services/translation-config.service';
import { ThemeService } from '../../core/services/theme.service';
import { GlossaryTerm, EntityType, Work } from '../../core/models';

@Component({
  selector: 'app-glossary',
  standalone: true,
  imports: [CommonModule, FormsModule, BaseChartDirective],
  templateUrl: './glossary.component.html',
  styleUrls: ['./glossary.component.scss'],
  animations: [
    trigger('listAnimation', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(10px)' }),
          stagger('50ms', [
            animate('200ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
  ],
})
export class GlossaryComponent implements OnInit {
  private glossaryService = inject(GlossaryService);
  private workService = inject(WorkService);
  private configService = inject(TranslationConfigService);
  private themeService = inject(ThemeService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  terms = signal<GlossaryTerm[]>([]);
  works = signal<Work[]>([]);
  languages = signal<{code: string, name: string}[]>([]);

  selectedWorkId = signal<number | null>(null);
  searchTerm = signal('');
  selectedEntityType = signal<EntityType | ''>('');
  isLoading = signal(false);
  isLoadingWorks = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  newTerm = {
    term: '',
    translation: '',
    entity_type: 'other' as EntityType,
    context: '',
    is_proper_noun: false,
    do_not_translate: false
  };

  editingTerm = signal<GlossaryTerm | null>(null);
  termTouched = false;

  entityTypes: EntityType[] = ['character', 'place', 'skill', 'item', 'spell', 'faction', 'title', 'race', 'other'];

  selectedWork = computed(() => {
    const id = this.selectedWorkId();
    return this.works().find(w => w.id === id) || null;
  });

  entityChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: [],
    datasets: [{
      data: [],
      backgroundColor: [],
      borderWidth: 0
    }]
  };

  entityChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          padding: 15,
          usePointStyle: true,
          pointStyle: 'circle'
        }
      }
    },
    cutout: '60%'
  };

  ngOnInit(): void {
    this.loadWorks();
    this.loadLanguages();
  }

  private loadWorks(): void {
    this.isLoadingWorks.set(true);
    this.workService.getAll(1, 100).subscribe({
      next: (response: WorkListResponse) => {
        this.works.set(response.items);
        this.isLoadingWorks.set(false);
        this.checkQueryParam();
      },
      error: (err) => {
        console.error('Failed to load works:', err);
        this.isLoadingWorks.set(false);
        this.errorMessage.set('Failed to load works');
      }
    });
  }

  private checkQueryParam(): void {
    const workIdParam = this.route.snapshot.queryParamMap.get('workId');
    if (workIdParam) {
      const workId = parseInt(workIdParam, 10);
      if (!isNaN(workId) && this.works().some(w => w.id === workId)) {
        this.selectedWorkId.set(workId);
        this.loadTerms();
      }
    }
  }

  private loadLanguages(): void {
    this.configService.getLanguages().subscribe({
      next: (langs) => this.languages.set(langs),
      error: (err) => console.error('Failed to load languages:', err),
    });
  }

  private loadTerms(): void {
    const workId = this.selectedWorkId();
    if (!workId) {
      this.terms.set([]);
      return;
    }

    this.isLoading.set(true);
    this.glossaryService.getAll(workId).subscribe({
      next: (terms) => {
        this.terms.set(terms);
        this.updateChartData(terms);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to load glossary terms');
        this.isLoading.set(false);
        console.error('Failed to load terms:', err);
      },
    });
  }

  onWorkChange(workId: string): void {
    const id = workId ? parseInt(workId, 10) : null;
    this.selectedWorkId.set(id);
    this.editingTerm.set(null);

    if (id) {
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: { workId: id },
        queryParamsHandling: 'merge'
      });
      this.loadTerms();
    } else {
      this.terms.set([]);
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: {}
      });
    }
  }

  private updateChartData(terms: GlossaryTerm[]): void {
    const entityCounts: Record<EntityType, number> = {
      character: 0,
      place: 0,
      skill: 0,
      item: 0,
      spell: 0,
      faction: 0,
      title: 0,
      race: 0,
      other: 0
    };

    terms.forEach(term => {
      entityCounts[term.entity_type]++;
    });

    const labels: string[] = [];
    const data: number[] = [];
    const colors: string[] = [];

    this.entityTypes.forEach(type => {
      if (entityCounts[type] > 0) {
        labels.push(type.charAt(0).toUpperCase() + type.slice(1));
        data.push(entityCounts[type]);
        colors.push(this.getEntityTypeColor(type));
      }
    });

    this.entityChartData.labels = labels;
    this.entityChartData.datasets[0].data = data;
    this.entityChartData.datasets[0].backgroundColor = colors;
  }

  get filteredTerms(): GlossaryTerm[] {
    const search = this.searchTerm().toLowerCase();
    let filtered = this.terms();

    if (this.selectedEntityType()) {
      filtered = filtered.filter(t => t.entity_type === this.selectedEntityType());
    }

    if (search) {
      filtered = filtered.filter((term) =>
        term.term.toLowerCase().includes(search) ||
        (term.translation && term.translation.toLowerCase().includes(search)) ||
        (term.context && term.context.toLowerCase().includes(search))
      );
    }

    return filtered;
  }

  getEntityTypeIcon(type: EntityType): string {
    const icons: Record<EntityType, string> = {
      character: '👤',
      place: '📍',
      skill: '⚡',
      item: '📦',
      spell: '✨',
      faction: '🏛️',
      title: '👑',
      race: '🧬',
      other: '📝'
    };
    return icons[type] || '📝';
  }

  getEntityTypeColor(type: EntityType): string {
    const colors: Record<EntityType, string> = {
      character: '#3b82f6',
      place: '#10b981',
      skill: '#f59e0b',
      item: '#8b5cf6',
      spell: '#ec4899',
      faction: '#6366f1',
      title: '#f97316',
      race: '#14b8a6',
      other: '#6b7280'
    };
    return colors[type] || '#6b7280';
  }

  getConfidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  addTerm(): void {
    this.termTouched = true;

    if (!this.newTerm.term.trim()) {
      this.errorMessage.set('Term is required');
      return;
    }

    const workId = this.selectedWorkId();
    if (!workId) {
      this.errorMessage.set('Please select a work first');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const selectedWork = this.selectedWork();
    const termToAdd = {
      work_id: workId,
      term: this.newTerm.term,
      translation: this.newTerm.translation || undefined,
      entity_type: this.newTerm.entity_type,
      context: this.newTerm.context || undefined,
      is_proper_noun: this.newTerm.is_proper_noun,
      source_lang: selectedWork?.source_lang || 'en',
      target_lang: selectedWork?.target_lang || 'es'
    };

    this.glossaryService.create(termToAdd).subscribe({
      next: (createdTerm) => {
        this.terms.update((terms) => [...terms, createdTerm]);
        this.updateChartData(this.terms());
        this.newTerm = {
          term: '',
          translation: '',
          entity_type: 'other',
          context: '',
          is_proper_noun: false,
          do_not_translate: false
        };
        this.termTouched = false;
        this.successMessage.set('Term added successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to add term');
        this.isLoading.set(false);
        console.error('Failed to add term:', err);
      },
    });
  }

  startEdit(term: GlossaryTerm): void {
    this.editingTerm.set({ ...term });
  }

  cancelEdit(): void {
    this.editingTerm.set(null);
  }

  saveEdit(): void {
    const term = this.editingTerm();
    if (!term) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.glossaryService.update(term.id, {
      term: term.term,
      translation: term.translation,
      context: term.context,
      is_proper_noun: term.is_proper_noun,
      do_not_translate: term.do_not_translate,
      is_verified: term.is_verified
    }).subscribe({
      next: (updatedTerm) => {
        this.terms.update((terms) =>
          terms.map((t) => (t.id === updatedTerm.id ? updatedTerm : t))
        );
        this.editingTerm.set(null);
        this.successMessage.set('Term updated successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to update term');
        this.isLoading.set(false);
        console.error('Failed to update term:', err);
      },
    });
  }

  deleteTerm(id: number): void {
    if (!confirm('Are you sure you want to delete this term?')) {
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.glossaryService.delete(id).subscribe({
      next: () => {
        this.terms.update((terms) => terms.filter((t) => t.id !== id));
        this.updateChartData(this.terms());
        this.successMessage.set('Term deleted successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to delete term');
        this.isLoading.set(false);
        console.error('Failed to delete term:', err);
      },
    });
  }

  clearFilters(): void {
    this.searchTerm.set('');
    this.selectedEntityType.set('');
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  get currentTheme() {
    return this.themeService.currentTheme();
  }
}
