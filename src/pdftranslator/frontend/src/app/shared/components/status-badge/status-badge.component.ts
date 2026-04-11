import { Component, Input } from '@angular/core';
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
  @Input() status: BadgeStatus = 'neutral';
  @Input() text = '';
  @Input() size: BadgeSize = 'medium';
  @Input() icon = '';

  getStatusClass(): string {
    return `badge-${this.status}`;
  }

  getSizeClass(): string {
    return `badge-${this.size}`;
  }
}
