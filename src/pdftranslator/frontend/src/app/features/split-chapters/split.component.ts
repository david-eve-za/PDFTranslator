import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-split',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './split.component.html',
  styleUrl: './split.component.scss'
})
export class SplitComponent {
  selectedWork: string | null = null;
  selectedVolume: string | null = null;
  volumeText = '';
  parsedChapters: any[] = [];
  isParsing = false;

  works = [
    { id: 1, title: 'The Great Adventure', volumes: 2 },
    { id: 2, title: 'Mystery of the Ancients', volumes: 1 },
    { id: 3, title: 'Dragon\'s Legacy', volumes: 2 }
  ];

  onWorkSelect(workId: string): void {
    this.selectedWork = workId;
    this.selectedVolume = null;
    this.volumeText = '';
    this.parsedChapters = [];
  }

  onVolumeSelect(volumeId: string): void {
    this.selectedVolume = volumeId;
    this.volumeText = this.getMockVolumeText();
    this.parsedChapters = [];
  }

  parseChapters(): void {
    this.isParsing = true;
    
    // Simulate parsing
    setTimeout(() => {
      this.parsedChapters = [
        { type: 'prologue', title: 'Prologue', content: 'In the beginning...' },
        { type: 'chapter', title: 'Chapter 1: The Journey Begins', content: 'Chapter 1 content...' },
        { type: 'chapter', title: 'Chapter 2: Into the Forest', content: 'Chapter 2 content...' },
        { type: 'epilogue', title: 'Epilogue', content: 'The end...' }
      ];
      this.isParsing = false;
    }, 1000);
  }

  private getMockVolumeText(): string {
    return `[===Type="Prologue"===]
In the beginning, there was only darkness...

[===End Block===]

[===Type="Chapter"===]
Chapter 1: The Journey Begins

Our hero embarks on a great adventure...

[===End Block===]

[===Type="Chapter"===]
Chapter 2: Into the Forest

The ancient forest loomed ahead...

[===End Block===]

[===Type="Epilogue"===]
And so the story ends, but the legend lives on...

[===End Block===]`;
  }

  getChapterTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      prologue: '📜',
      chapter: '📖',
      epilogue: '🏁'
    };
    return icons[type] || '📄';
  }
}
