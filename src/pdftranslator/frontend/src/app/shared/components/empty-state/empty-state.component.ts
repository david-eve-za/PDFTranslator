import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './empty-state.component.html',
  styleUrl: './empty-state.component.scss'
})
export class EmptyStateComponent {
  icon = input('📭');
  title = input('No data available');
  message = input('');
  actionLabel = input('');
  action = output<void>();

  onAction(): void {
    this.action.emit();
  }
}
