import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type SkeletonVariant = 'card' | 'list' | 'grid' | 'text' | 'stat';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './skeleton-loader.component.html',
  styleUrls: ['./skeleton-loader.component.scss'],
})
export class SkeletonLoaderComponent {
  @Input() variant: SkeletonVariant = 'card';
  @Input() count: number = 1;
  @Input() rows: number = 3;

  get items(): number[] {
    return Array(this.count).fill(0);
  }

  get textRows(): number[] {
    return Array(this.rows).fill(0);
  }
}
