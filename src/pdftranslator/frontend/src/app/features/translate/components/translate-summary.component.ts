import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-translate-summary',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './translate-summary.component.html',
  styleUrl: './translate-summary.component.scss',
})
export class TranslateSummaryComponent {
  successCount = input(0);
  failureCount = input(0);
  skippedCount = input(0);

  translateAgain = output<void>();
}
