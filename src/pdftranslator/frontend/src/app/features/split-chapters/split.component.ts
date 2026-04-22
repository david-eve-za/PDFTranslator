import { Component, OnInit, OnDestroy, signal, inject, viewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { WorkService, WorkListResponse } from '../../core/services/work.service';
import { VolumeService, VolumeListResponse } from '../../core/services/volume.service';
import { SplitService, ParsedBlock } from '../../core/services/split.service';
import { Work, Volume } from '../../core/models';

type BlockType = 'Prologue' | 'Chapter' | 'Epilogue';

@Component({
  selector: 'app-split',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './split.component.html',
  styleUrl: './split.component.scss'
})
export class SplitComponent implements OnInit, OnDestroy {
  private workService = inject(WorkService);
  private volumeService = inject(VolumeService);
  private splitService = inject(SplitService);
  private route = inject(ActivatedRoute);

  private messageTimeoutId: ReturnType<typeof setTimeout> | null = null;

  textareaElement = viewChild<ElementRef<HTMLTextAreaElement>>('textareaRef');

  works = signal<Work[]>([]);
  volumes = signal<Volume[]>([]);
  selectedWorkId = signal<number | null>(null);
  selectedVolumeId = signal<number | null>(null);
  volumeText = signal('');
  parsedBlocks = signal<ParsedBlock[]>([]);

  isLoading = signal(false);
  isProcessing = signal(false);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  showTypeModal = signal(false);
  selectedBlockType = signal<BlockType>('Chapter');
  blockTitle = signal('');

  ngOnInit(): void {
    this.loadWorks();
  }

  ngOnDestroy(): void {
    this.clearMessageTimeout();
  }

  private clearMessageTimeout(): void {
    if (this.messageTimeoutId) {
      clearTimeout(this.messageTimeoutId);
      this.messageTimeoutId = null;
    }
  }

  private showSuccess(message: string, duration: number = 5000): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(message);
    this.messageTimeoutId = setTimeout(() => {
      this.successMessage.set(null);
      this.messageTimeoutId = null;
    }, duration);
  }

  private showError(message: string): void {
    this.clearMessageTimeout();
    this.successMessage.set(null);
    this.errorMessage.set(message);
  }

  private clearMessages(): void {
    this.clearMessageTimeout();
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  private loadWorks(): void {
    this.isLoading.set(true);
    this.workService.getAll(1, 100).subscribe({
      next: (response: WorkListResponse) => {
        this.works.set(response.items);
        this.isLoading.set(false);
        this.checkQueryParam();
      },
      error: (err) => {
        this.showError('Failed to load works');
        this.isLoading.set(false);
        console.error('Failed to load works:', err);
      }
    });
  }

  private checkQueryParam(): void {
    const workIdParam = this.route.snapshot.queryParamMap.get('workId');
    if (workIdParam) {
      const workId = parseInt(workIdParam, 10);
      if (!isNaN(workId)) {
        this.onWorkSelect(workId.toString());
      }
    }
  }

  onWorkSelect(workId: string): void {
    const id = parseInt(workId, 10);
    if (isNaN(id)) {
      this.selectedWorkId.set(null);
      this.volumes.set([]);
      return;
    }

    this.selectedWorkId.set(id);
    this.selectedVolumeId.set(null);
    this.volumeText.set('');
    this.parsedBlocks.set([]);
    this.clearMessages();

    this.volumeService.getByWorkId(id).subscribe({
      next: (response: VolumeListResponse) => {
        this.volumes.set(response.items.sort((a, b) => a.volume_number - b.volume_number));
      },
      error: (err) => {
        this.showError('Failed to load volumes');
        console.error('Failed to load volumes:', err);
      }
    });
  }

  onVolumeSelect(volumeId: string): void {
    const id = parseInt(volumeId, 10);
    if (isNaN(id)) {
      this.selectedVolumeId.set(null);
      this.volumeText.set('');
      return;
    }

    this.selectedVolumeId.set(id);
    this.parsedBlocks.set([]);
    this.clearMessages();

    this.volumeService.getById(id).subscribe({
      next: (volume) => {
        this.volumeText.set(volume.full_text || '');
      },
      error: (err) => {
        this.showError('Failed to load volume text');
        console.error('Failed to load volume:', err);
      }
    });
  }

  openTypeModal(): void {
    this.selectedBlockType.set('Chapter');
    this.blockTitle.set('');
    this.showTypeModal.set(true);
  }

  cancelTypeModal(): void {
    this.showTypeModal.set(false);
  }

  insertStartMarker(): void {
    const textarea = this.textareaElement()?.nativeElement;
    if (!textarea) return;

    const position = textarea.selectionStart;
    const type = this.selectedBlockType();
    const title = this.blockTitle();

    let marker = `[===Type="${type}"`;
    if (title.trim()) {
      marker += ` Title="${title.trim()}"`;
    }
    marker += `===]\n`;

    const currentText = this.volumeText();
    const newText = currentText.slice(0, position) + marker + currentText.slice(position);
    this.volumeText.set(newText);

    this.showTypeModal.set(false);

    setTimeout(() => {
      textarea.focus();
      const newPosition = position + marker.length;
      textarea.setSelectionRange(newPosition, newPosition);
    }, 0);
  }

  insertEndMarker(): void {
    const textarea = this.textareaElement()?.nativeElement;
    if (!textarea) return;

    const position = textarea.selectionStart;
    const marker = '\n[===End Block===]\n';

    const currentText = this.volumeText();
    const newText = currentText.slice(0, position) + marker + currentText.slice(position);
    this.volumeText.set(newText);

    setTimeout(() => {
      textarea.focus();
      const newPosition = position + marker.length;
      textarea.setSelectionRange(newPosition, newPosition);
    }, 0);
  }

  previewBlocks(): void {
    this.isLoading.set(true);
    this.clearMessages();

    this.splitService.preview(this.volumeText()).subscribe({
      next: (response) => {
        if (response.has_errors) {
          this.showError(response.error_message || 'Parse error');
        } else {
          this.parsedBlocks.set(response.blocks);
        }
        this.isLoading.set(false);
      },
      error: (err) => {
        this.showError('Failed to preview blocks');
        this.isLoading.set(false);
        console.error('Preview error:', err);
      }
    });
  }

  processAndSave(): void {
    const volumeId = this.selectedVolumeId();
    if (!volumeId) {
      this.showError('No volume selected');
      return;
    }

    this.isProcessing.set(true);
    this.clearMessages();

    this.splitService.process(volumeId, this.volumeText()).subscribe({
      next: (response) => {
        if (response.success) {
          this.parsedBlocks.set([]);
          this.isProcessing.set(false);
          this.showSuccess(`Successfully created ${response.chapters_created} chapter(s)`);
        } else {
          this.showError(response.error_message || 'Failed to process');
          this.isProcessing.set(false);
        }
      },
      error: (err) => {
        this.showError('Failed to process split');
        this.isProcessing.set(false);
        console.error('Process error:', err);
      }
    });
  }

  clearPreview(): void {
    this.parsedBlocks.set([]);
  }

  getBlockTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      Prologue: '📜',
      Chapter: '📖',
      Epilogue: '🏁'
    };
    return icons[type] || '📄';
  }
}
