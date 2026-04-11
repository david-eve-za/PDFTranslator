import { Component, ViewChild } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate, query } from '@angular/animations';
import { ThemeService } from './core/services/theme.service';
import { NotificationToastComponent } from './shared/components/notification-toast/notification-toast.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, NotificationToastComponent],
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
  animations: [
    trigger('routeAnimations', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(10px)' }),
        ], { optional: true }),
        query(':leave', [
          style({ opacity: 1, transform: 'translateY(0)' }),
          animate('200ms ease-out', style({ opacity: 0, transform: 'translateY(-10px)' })),
        ], { optional: true }),
        query(':enter', [
          animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
        ], { optional: true }),
      ]),
    ]),
  ],
})
export class App {
  @ViewChild(RouterOutlet) routerOutlet!: RouterOutlet;

  constructor(private themeService: ThemeService) {}

  get currentTheme() {
    return this.themeService.currentTheme();
  }

  get currentYear(): number {
    return new Date().getFullYear();
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }
}
