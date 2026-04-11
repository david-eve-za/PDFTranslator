import { Component, Input, Output, EventEmitter, signal, OnInit, InputSignal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Language } from '../../../core/models/translation.models';

@Component({
  selector: 'app-language-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './language-selector.component.html',
  styleUrls: ['./language-selector.component.scss'],
})
export class LanguageSelectorComponent implements OnInit {
  @Input() label = 'Language';
  @Input() placeholder = 'Select a language';
  @Input() languages: Language[] = [];
  private _selectedLanguage = signal<string>('');

  buttonId = `language-selector-${Math.random().toString(36).substring(2, 9)}`;

  @Input()
  set selectedLanguage(value: string | InputSignal<string>) {
    if (typeof value === 'string') {
      this._selectedLanguage.set(value);
    }
  }
  
  get selectedLanguageValue(): string {
    return this._selectedLanguage();
  }
  
  @Output() languageChange = new EventEmitter<string>();

  isOpen = signal(false);
  searchTerm = signal('');

  ngOnInit(): void {
    if (this.languages.length === 0) {
      this.languages = [
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
    }
  }

  get filteredLanguages(): Language[] {
    const term = this.searchTerm().toLowerCase();
    if (!term) return this.languages;

    return this.languages.filter(
      (lang) =>
        lang.name.toLowerCase().includes(term) ||
        lang.code.toLowerCase().includes(term) ||
        (lang.nativeName && lang.nativeName.toLowerCase().includes(term))
    );
  }

  get selectedLanguageName(): string {
    const code = this._selectedLanguage();
    const lang = this.languages.find((l) => l.code === code);
    return lang ? `${lang.name} (${lang.nativeName || lang.code})` : this.placeholder;
  }

  toggleDropdown(): void {
    this.isOpen.update((open) => !open);
    if (!this.isOpen()) {
      this.searchTerm.set('');
    }
  }

  selectLanguage(code: string): void {
    this._selectedLanguage.set(code);
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
