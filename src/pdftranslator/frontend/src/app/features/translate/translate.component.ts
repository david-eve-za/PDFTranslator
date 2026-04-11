import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { ThemeService } from '../../core/services/theme.service';
import { Language, Provider, TranslationResponse } from '../../core/models/translation.models';
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
  private apiService = inject(ApiService);
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
    this.apiService.getLanguages().subscribe({
      next: (langs) => this.languages.set(langs),
      error: (err) => console.error('Failed to load languages:', err),
    });
  }

  private loadProviders(): void {
    this.apiService.getProviders().subscribe({
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

    this.progressStatus.set('uploading');
    this.progressValue.set(0);
    this.progressMessage.set('Preparing file for upload...');
    this.errorMessage.set(null);
    this.downloadUrl.set(null);

    this.apiService
      .translateFile(
        file,
        this.sourceLanguage(),
        this.targetLanguage(),
        this.selectedProvider(),
        (progressEvent) => {
          this.progressStatus.set('uploading');
          this.progressValue.set(progressEvent.percentage);
          this.progressMessage.set(
            `Uploading... ${progressEvent.percentage}%`
          );
        }
      )
      .subscribe({
        next: (response: TranslationResponse) => {
          this.handleTranslationResponse(response);
        },
        error: (err) => {
          this.progressStatus.set('error');
          this.errorMessage.set(
            err.message || 'An error occurred during translation'
          );
        },
      });
  }

  private handleTranslationResponse(response: TranslationResponse): void {
    switch (response.status) {
      case 'pending':
      case 'processing':
        this.progressStatus.set('processing');
        this.progressValue.set(response.progress);
        this.progressMessage.set(`Processing... ${response.progress}%`);
        setTimeout(() => {
          this.pollTranslationStatus(response.id);
        }, 2000);
        break;
      case 'completed':
        this.progressStatus.set('completed');
        this.progressValue.set(100);
        this.progressMessage.set('Translation completed successfully!');
        this.downloadUrl.set(response.downloadUrl || null);
        break;
      case 'error':
        this.progressStatus.set('error');
        this.errorMessage.set(response.error || 'Translation failed');
        break;
    }
  }

  private pollTranslationStatus(id: string): void {
    this.apiService.getTranslationStatus(id).subscribe({
      next: (response) => this.handleTranslationResponse(response),
      error: (err) => {
        this.progressStatus.set('error');
        this.errorMessage.set(err.message || 'Failed to check status');
      },
    });
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
