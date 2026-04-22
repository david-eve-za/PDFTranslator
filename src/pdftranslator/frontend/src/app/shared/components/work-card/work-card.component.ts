import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Work } from '../../../core/models';

@Component({
  selector: 'app-work-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './work-card.component.html',
  styleUrl: './work-card.component.scss'
})
export class WorkCardComponent {
  work = input.required<Work>();
  translate = output<number>();
  glossary = output<number>();
  view = output<number>();

  getProgressPercentage(): number {
    return this.work().total_chapters > 0
      ? Math.round((this.work().translated_chapters / this.work().total_chapters) * 100)
      : 0;
  }

  getStatusClass(): string {
    const progress = this.getProgressPercentage();
    if (progress === 100) return 'complete';
    if (progress > 0) return 'in-progress';
    return 'not-started';
  }

  onTranslate(): void {
    this.translate.emit(this.work().id);
  }

  onGlossary(): void {
    this.glossary.emit(this.work().id);
  }

  onView(): void {
    this.view.emit(this.work().id);
  }
}
