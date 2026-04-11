import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notificationSubject = new Subject<Notification>();
  private removeSubject = new Subject<string>();

  notifications$: Observable<Notification> = this.notificationSubject.asObservable();
  remove$: Observable<string> = this.removeSubject.asObservable();

  private generateId(): string {
    return `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  show(notification: Omit<Notification, 'id'>): string {
    const id = this.generateId();
    this.notificationSubject.next({ ...notification, id });

    if (notification.duration !== 0) {
      setTimeout(() => {
        this.remove(id);
      }, notification.duration || 5000);
    }

    return id;
  }

  success(message: string, duration?: number): string {
    return this.show({ type: 'success', message, duration });
  }

  error(message: string, duration?: number): string {
    return this.show({ type: 'error', message, duration });
  }

  warning(message: string, duration?: number): string {
    return this.show({ type: 'warning', message, duration });
  }

  info(message: string, duration?: number): string {
    return this.show({ type: 'info', message, duration });
  }

  remove(id: string): void {
    this.removeSubject.next(id);
  }

  clear(): void {
    this.notificationSubject.next({ id: 'clear-all', type: 'info', message: '' });
  }
}
