import { Component, input, output, model, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Language } from '../../../core/models/translation.models';

@Component({
  selector: 'app-language-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './language-selector.component.html',
  styleUrl: './language-selector.component.scss',
})
export class LanguageSelectorComponent implements OnInit {
  label = input('Language');
  placeholder = input('Select a language');
  languages = input<Language[]>([]);
  selectedLanguage = model<string>('');

  buttonId = `language-selector-${Math.random().toString(36).substring(2, 9)}`;

  languageChange = output<string>();

  isOpen = model(false);
  searchTerm = model('');

  private defaultLanguages: Language[] = [
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'es', name: 'Spanish', nativeName: 'Español' },
    { code: 'fr', name: 'French', nativeName: 'Français' },
    { code: 'de', name: 'German', nativeName: 'Deutsch' },
    { code: 'it', name: 'Italian', nativeName: 'Italiano' },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
    { code: 'zh', name: 'Chinese', nativeName: '中文' },
    { code: 'ja', name: 'Japanese', nativeName: '日本語' },
    { code: 'ko', name: 'Korean', nativeName: '한국어' },
    { code: 'ru', name: 'Russian', nativeName: 'Русский' },
  ];

  ngOnInit(): void {
    if (this.languages().length === 0) {
    }
  }

  get effectiveLanguages(): Language[] {
    const langs = this.languages();
    return langs.length > 0 ? langs : this.defaultLanguages;
  }

  get filteredLanguages(): Language[] {
    const term = this.searchTerm().toLowerCase();
    if (!term) return this.effectiveLanguages;

    return this.effectiveLanguages.filter(
      (lang) =>
        lang.name.toLowerCase().includes(term) ||
        lang.code.toLowerCase().includes(term) ||
        (lang.nativeName && lang.nativeName.toLowerCase().includes(term))
    );
  }

  get selectedLanguageName(): string {
    const code = this.selectedLanguage();
    const lang = this.effectiveLanguages.find((l) => l.code === code);
    return lang ? `${lang.name} (${lang.nativeName || lang.code})` : this.placeholder();
  }

  toggleDropdown(): void {
    this.isOpen.update((open) => !open);
    if (!this.isOpen()) {
      this.searchTerm.set('');
    }
  }

  selectLanguage(code: string): void {
    this.selectedLanguage.set(code);
    this.languageChange.emit(code);
    this.isOpen.set(false);
    this.searchTerm.set('');
  }

  onSearchInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm.set(input.value);
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.isOpen.set(false);
    }
  }
}
