import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, Notification } from '../../services/notification.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-notification-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notification-toast.component.html',
  styleUrl: './notification-toast.component.scss'
})
export class NotificationToastComponent implements OnInit, OnDestroy {
  private notificationService = inject(NotificationService);
  private destroy$ = new Subject<void>();

  notifications: (Notification & { visible: boolean })[] = [];

  ngOnInit(): void {
    this.notificationService.notifications$
      .pipe(takeUntil(this.destroy$))
      .subscribe((notif) => {
        if (notif.id === 'clear-all') {
          this.notifications = [];
          return;
        }
        this.notifications.push({ ...notif, visible: true });
      });

    this.notificationService.remove$
      .pipe(takeUntil(this.destroy$))
      .subscribe((id) => {
        const index = this.notifications.findIndex(n => n.id === id);
        if (index !== -1) {
          this.notifications[index].visible = false;
          setTimeout(() => {
            this.notifications = this.notifications.filter(n => n.id !== id);
          }, 300);
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  remove(id: string): void {
    this.notificationService.remove(id);
  }

  getIcon(type: string): string {
    const icons: Record<string, string> = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };
    return icons[type] || 'ℹ';
  }
}
