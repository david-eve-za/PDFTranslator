import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { SettingsService } from '../../core/services/settings.service';
import { SubstitutionRuleService } from '../../core/services/substitution-rule.service';
import { Settings, SubstitutionRule, SubstitutionRuleCreate } from '../../core/models';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
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
export class SettingsComponent implements OnInit {
  private settingsService = inject(SettingsService);
  private ruleService = inject(SubstitutionRuleService);

activeTab = signal<'llm' | 'database' | 'document' | 'nlp' | 'paths' | 'rules'>('llm');
settings = signal<Settings | null>(null);
rules = signal<SubstitutionRule[]>([]);

isLoading = signal(false);
isSaving = signal(false);
errorMessage = signal<string | null>(null);
successMessage = signal<string | null>(null);
restartRequired = signal(false);

newRule: SubstitutionRuleCreate = {
  name: '',
  pattern: '',
  replacement: '',
  description: '',
  is_active: true,
  apply_on_extract: true,
};

editingRule = signal<SubstitutionRule | null>(null);

readonly tabs = [
  { key: 'llm' as const, label: 'LLM', icon: '🤖' },
  { key: 'database' as const, label: 'Database', icon: '🗄️' },
  { key: 'document' as const, label: 'Document', icon: '📄' },
  { key: 'nlp' as const, label: 'NLP', icon: '🧠' },
  { key: 'paths' as const, label: 'Paths', icon: '📁' },
  { key: 'rules' as const, label: 'Rules', icon: '🔄' },
];

  ngOnInit(): void {
    this.loadSettings();
    this.loadRules();
  }

  private loadSettings(): void {
    this.isLoading.set(true);
    this.settingsService.getSettings().subscribe({
      next: (data) => {
        this.settings.set(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('Failed to load settings');
        this.isLoading.set(false);
        console.error('Failed to load settings:', err);
      },
    });
  }

  private loadRules(): void {
    this.ruleService.getAll().subscribe({
      next: (data) => this.rules.set(data),
      error: (err) => console.error('Failed to load rules:', err),
    });
  }

  setActiveTab(tab: 'llm' | 'database' | 'document' | 'nlp' | 'paths' | 'rules'): void {
    this.activeTab.set(tab);
  }

  updateOcrLanguages(value: string): void {
    const current = this.settings();
    if (current) {
      current.document.ocr_languages = value.split(',').map((s) => s.trim());
    }
  }

  updateEntityTypes(value: string): void {
    const current = this.settings();
    if (current) {
      current.nlp.entity_types = value.split(',').map((s) => s.trim());
    }
  }

  saveSettings(): void {
    const current = this.settings();
    if (!current) return;

    this.isSaving.set(true);
    this.errorMessage.set(null);

    this.settingsService.updateSettings(current).subscribe({
      next: (result) => {
        this.successMessage.set(result.message);
        this.restartRequired.set(result.restart_required);
        this.isSaving.set(false);
        setTimeout(() => this.successMessage.set(null), 5000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to save settings');
        this.isSaving.set(false);
        console.error('Failed to save settings:', err);
      },
    });
  }

  restartBackend(): void {
    this.settingsService.requestRestart().subscribe({
      next: (result) => {
        this.successMessage.set(result.message);
        this.restartRequired.set(false);
        setTimeout(() => this.successMessage.set(null), 5000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to request restart');
        console.error('Failed to request restart:', err);
      },
    });
  }

  addRule(): void {
    if (!this.newRule.name.trim() || !this.newRule.pattern.trim()) {
      this.errorMessage.set('Name and pattern are required');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.ruleService.create(this.newRule).subscribe({
      next: (created) => {
        this.rules.update((rules) => [...rules, created]);
        this.newRule = {
          name: '',
          pattern: '',
          replacement: '',
          description: '',
          is_active: true,
          apply_on_extract: true,
        };
        this.successMessage.set('Rule created successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to create rule');
        this.isLoading.set(false);
        console.error('Failed to create rule:', err);
      },
    });
  }

  startEditRule(rule: SubstitutionRule): void {
    this.editingRule.set({ ...rule });
  }

  cancelEditRule(): void {
    this.editingRule.set(null);
  }

  saveRuleEdit(): void {
    const rule = this.editingRule();
    if (!rule) return;

    this.isLoading.set(true);

    this.ruleService.update(rule.id, {
      name: rule.name,
      pattern: rule.pattern,
      replacement: rule.replacement,
      description: rule.description,
      is_active: rule.is_active,
      apply_on_extract: rule.apply_on_extract,
    }).subscribe({
      next: (updated) => {
        this.rules.update((rules) =>
          rules.map((r) => (r.id === updated.id ? updated : r))
        );
        this.editingRule.set(null);
        this.successMessage.set('Rule updated successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to update rule');
        this.isLoading.set(false);
        console.error('Failed to update rule:', err);
      },
    });
  }

  deleteRule(id: number): void {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    this.isLoading.set(true);
    this.ruleService.delete(id).subscribe({
      next: () => {
        this.rules.update((rules) => rules.filter((r) => r.id !== id));
        this.successMessage.set('Rule deleted successfully!');
        this.isLoading.set(false);
        setTimeout(() => this.successMessage.set(null), 3000);
      },
      error: (err) => {
        this.errorMessage.set('Failed to delete rule');
        this.isLoading.set(false);
        console.error('Failed to delete rule:', err);
      },
    });
  }

  toggleRuleActive(rule: SubstitutionRule): void {
    this.ruleService.update(rule.id, { is_active: !rule.is_active }).subscribe({
      next: (updated) => {
        this.rules.update((rules) =>
          rules.map((r) => (r.id === updated.id ? updated : r))
        );
      },
      error: (err) => console.error('Failed to toggle rule:', err),
    });
  }

  testPattern(pattern: string, testText: string): { matches: boolean; result: string } | null {
    if (!pattern || !testText) return null;
    try {
      const regex = new RegExp(pattern, 'g');
      const matches = regex.test(testText);
      const result = testText.replace(regex, this.editingRule()?.replacement || '');
      return { matches, result };
    } catch {
      return null;
    }
  }
}
