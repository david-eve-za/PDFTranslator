import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { ThemeService } from '../../core/services/theme.service';
import { GlossaryTerm, GlossaryCreateRequest, Language } from '../../core/models/translation.models';
import { LanguageSelectorComponent } from '../../shared/components/language-selector/language-selector.component';

@Component({
  selector: 'app-glossary',
  standalone: true,
  imports: [CommonModule, FormsModule, LanguageSelectorComponent],
  templateUrl: './glossary.component.html',
  styleUrls: ['./glossary.component.scss'],
})
export class GlossaryComponent implements OnInit {
  private apiService = inject(ApiService);
  private themeService = inject(ThemeService);

  terms = signal<GlossaryTerm[]>([]);
  languages = signal<Language[]>([]);
  
  newTerm = signal<GlossaryCreateRequest>({
    sourceTerm: '',
    targetTerm: '',
    sourceLanguage: 'en',
    targetLanguage: 'es',
    context: '',
  });

  editingTerm = signal<GlossaryTerm | null>(null);
  searchTerm = signal('');
  isLoading = signal(false);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.loadLanguages();
    this.loadTerms();
  }

  private loadLanguages(): void {
    this.apiService.getLanguages().subscribe({
      next: (langs) => this.languages.set(langs),
      error: (err) => console.error('Failed to load languages:', err),
    });
  }

  private loadTerms(): void {
    this.isLoading.set(true);
    this.apiService.getGlossaryTerms().subscribe({
      next: (terms) => {
        this.terms.set(terms);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to load glossary terms');
        this.isLoading.set(false);
        console.error('Failed to load terms:', err);
      },
    });
  }

  get filteredTerms(): GlossaryTerm[] {
    const search = this.searchTerm().toLowerCase();
    if (!search) return this.terms();

    return this.terms().filter((term) =>
      term.sourceTerm.toLowerCase().includes(search) ||
      term.targetTerm.toLowerCase().includes(search) ||
      (term.context && term.context.toLowerCase().includes(search))
    );
  }

  onSourceLanguageChange(code: string): void {
    this.newTerm.update((term) => ({ ...term, sourceLanguage: code }));
  }

  onTargetLanguageChange(code: string): void {
    this.newTerm.update((term) => ({ ...term, targetLanguage: code }));
  }

  addTerm(): void {
    const term = this.newTerm();
    if (!term.sourceTerm.trim() || !term.targetTerm.trim()) {
      this.errorMessage.set('Both source and target terms are required');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.apiService.createGlossaryTerm(term).subscribe({
      next: (createdTerm) => {
        this.terms.update((terms) => [...terms, createdTerm]);
        this.newTerm.set({
          sourceTerm: '',
          targetTerm: '',
          sourceLanguage: 'en',
          targetLanguage: 'es',
          context: '',
        });
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

    this.apiService.updateGlossaryTerm(term).subscribe({
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

    this.apiService.deleteGlossaryTerm(id).subscribe({
      next: () => {
        this.terms.update((terms) => terms.filter((t) => t.id !== id));
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

  toggleTheme(): void {
    this.themeService.toggle();
  }

  get currentTheme() {
    return this.themeService.currentTheme();
  }
}
