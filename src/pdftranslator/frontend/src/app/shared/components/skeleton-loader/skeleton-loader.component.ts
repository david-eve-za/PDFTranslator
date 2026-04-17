import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type SkeletonVariant = 'card' | 'list' | 'grid' | 'text' | 'stat';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './skeleton-loader.component.html',
  styleUrl: './skeleton-loader.component.scss',
})
export class SkeletonLoaderComponent {
  variant = input<SkeletonVariant>('card');
  count = input(1);
  rows = input(3);

  get items(): number[] {
    return Array(this.count()).fill(0);
  }

  get textRows(): number[] {
    return Array(this.rows()).fill(0);
  }
}
