import { Card } from './card';
import { TaskBadge } from './task-badge';
import type { FileItem, TaskStatus } from '../../types';

interface FileCardProps {
  file: FileItem;
  taskStatus?: TaskStatus;
  isSelected: boolean;
  onClick: () => void;
  onRetryTask: (taskType: string) => void;
}

const fileIcons: Record<string, string> = {
  pdf: '📄',
  epub: '📘',
  doc: '📝',
  docx: '📝',
};

export function FileCard({ file, taskStatus, isSelected, onClick, onRetryTask }: FileCardProps) {
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card
      className={`p-4 cursor-pointer transition-all ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'hover:shadow-md'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">{fileIcons[file.type]}</span>
          <div>
            <h3 className="font-medium text-gray-900">{file.name}</h3>
            <p className="text-sm text-gray-500">{formatSize(file.size)}</p>
          </div>
        </div>
      </div>

      {taskStatus && (
        <div className="space-y-2">
          <TaskBadge taskName="Chapters" taskState={taskStatus.splitChapters} />
          <TaskBadge taskName="Glossary" taskState={taskStatus.glossary} />
          <TaskBadge taskName="Translated" taskState={taskStatus.translated} />
          <TaskBadge
            taskName="Audio"
            taskState={taskStatus.audioGenerated}
            onRetry={() => onRetryTask('audioGenerated')}
          />
        </div>
      )}
    </Card>
  );
}
