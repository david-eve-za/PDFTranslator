import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ThemeService } from './core/services/theme.service';
import { NotificationToastComponent } from './shared/components/notification-toast/notification-toast.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, NotificationToastComponent],
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
})
export class App {
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
