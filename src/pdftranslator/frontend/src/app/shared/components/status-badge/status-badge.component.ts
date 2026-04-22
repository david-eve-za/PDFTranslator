import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type BadgeStatus = 'success' | 'warning' | 'error' | 'info' | 'neutral';
export type BadgeSize = 'small' | 'medium' | 'large';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.scss'
})
export class StatusBadgeComponent {
  status = input<BadgeStatus>('neutral');
  text = input('');
  size = input<BadgeSize>('medium');
  icon = input('');

  getStatusClass(): string {
    return `badge-${this.status()}`;
  }

  getSizeClass(): string {
    return `badge-${this.size()}`;
  }
}
