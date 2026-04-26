import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-translate-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './translate-config.component.html',
  styleUrl: './translate-config.component.scss',
})
export class TranslateConfigComponent {
  sourceLang = input('en');
  targetLang = input('es');
  skipTranslated = signal(true);
  dryRun = signal(false);

  configChanged = output<{ skip_translated: boolean; dry_run: boolean }>();

  onSkipTranslatedChange(event: Event): void {
    const checkbox = event.target as HTMLInputElement;
    this.skipTranslated.set(checkbox.checked);
    this.emitConfig();
  }

  onDryRunChange(event: Event): void {
    const checkbox = event.target as HTMLInputElement;
    this.dryRun.set(checkbox.checked);
    this.emitConfig();
  }

  private emitConfig(): void {
    this.configChanged.emit({
      skip_translated: this.skipTranslated(),
      dry_run: this.dryRun(),
    });
  }
}
