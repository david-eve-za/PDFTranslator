import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslationConfigService, Language, Provider } from '../../core/services/translation-config.service';
import { ThemeService } from '../../core/services/theme.service';
import { FileUploadComponent } from '../../shared/components/file-upload/file-upload.component';
import { LanguageSelectorComponent } from '../../shared/components/language-selector/language-selector.component';
import { ProgressIndicatorComponent, ProgressStatus } from '../../shared/components/progress-indicator/progress-indicator.component';

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FileUploadComponent,
    LanguageSelectorComponent,
    ProgressIndicatorComponent,
  ],
  templateUrl: './translate.component.html',
  styleUrls: ['./translate.component.scss'],
})
export class TranslateComponent implements OnInit {
  private configService = inject(TranslationConfigService);
  private themeService = inject(ThemeService);

  languages = signal<Language[]>([]);
  providers = signal<Provider[]>([]);
  
  selectedFile = signal<File | null>(null);
  sourceLanguage = signal('en');
  targetLanguage = signal('es');
  selectedProvider = signal<string>('');

  progressStatus = signal<ProgressStatus>('idle');
  progressValue = signal(0);
  progressMessage = signal<string | null>(null);
  
  downloadUrl = signal<string | null>(null);
  errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.loadLanguages();
    this.loadProviders();
  }

  private loadLanguages(): void {
    this.configService.getLanguages().subscribe({
      next: (langs) => this.languages.set(langs),
      error: (err) => console.error('Failed to load languages:', err),
    });
  }

  private loadProviders(): void {
    this.configService.getProviders().subscribe({
      next: (provs) => {
        this.providers.set(provs);
        if (provs.length > 0) {
          this.selectedProvider.set(provs[0].id);
        }
      },
      error: (err) => console.error('Failed to load providers:', err),
    });
  }

  onFileSelected(file: File): void {
    this.selectedFile.set(file);
    this.errorMessage.set(null);
    this.downloadUrl.set(null);
  }

  onSourceLanguageChange(code: string): void {
    this.sourceLanguage.set(code);
  }

  onTargetLanguageChange(code: string): void {
    this.targetLanguage.set(code);
  }

  swapLanguages(): void {
    const temp = this.sourceLanguage();
    this.sourceLanguage.set(this.targetLanguage());
    this.targetLanguage.set(temp);
  }

  onProviderChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.selectedProvider.set(select.value);
  }

  canTranslate(): boolean {
    return (
      this.selectedFile() !== null &&
      this.sourceLanguage() !== '' &&
      this.targetLanguage() !== ''
    );
  }

  startTranslation(): void {
    const file = this.selectedFile();
    if (!file || !this.canTranslate()) {
      return;
    }

    // Simulate translation with mock data
    this.progressStatus.set('uploading');
    this.progressValue.set(0);
    this.progressMessage.set('Preparing file for upload...');
    this.errorMessage.set(null);
    this.downloadUrl.set(null);

    // Simulate upload progress
    let progress = 0;
    const uploadInterval = setInterval(() => {
      progress += 10;
      this.progressValue.set(progress);
      this.progressMessage.set(`Uploading... ${progress}%`);
      
      if (progress >= 100) {
        clearInterval(uploadInterval);
        this.simulateProcessing();
      }
    }, 200);
  }

  private simulateProcessing(): void {
    this.progressStatus.set('processing');
    this.progressValue.set(0);
    this.progressMessage.set('Processing translation...');

    let progress = 0;
    const processInterval = setInterval(() => {
      progress += 5;
      this.progressValue.set(progress);
      this.progressMessage.set(`Translating... ${progress}%`);
      
      if (progress >= 100) {
        clearInterval(processInterval);
        this.progressStatus.set('completed');
        this.progressMessage.set('Translation completed successfully!');
        this.downloadUrl.set('mock://download/translated-document.pdf');
      }
    }, 150);
  }

  downloadResult(): void {
    const url = this.downloadUrl();
    if (url) {
      window.open(url, '_blank');
    }
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  get currentTheme() {
    return this.themeService.currentTheme();
  }
}
