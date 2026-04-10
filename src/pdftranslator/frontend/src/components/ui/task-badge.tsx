import { Badge } from './badge';
import type { TaskState } from '../../types';

interface TaskBadgeProps {
  taskName: string;
  taskState: TaskState;
  onRetry?: () => void;
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-800',
  'in-progress': 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const statusIcons = {
  pending: '⏳',
  'in-progress': '⏳',
  completed: '✓',
  failed: '✗',
};

export function TaskBadge({ taskName, taskState, onRetry }: TaskBadgeProps) {
  const { status, progress, error } = taskState;

  return (
    <div className="flex items-center space-x-2">
      <Badge className={statusColors[status]}>
        <span className="mr-1">{statusIcons[status]}</span>
        {taskName}
        {status === 'in-progress' && progress !== undefined && ` (${progress}%)`}
      </Badge>
      {status === 'failed' && onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Retry
        </button>
      )}
      {status === 'failed' && error && (
        <span className="text-xs text-red-600" title={error}>
          {error.substring(0, 30)}...
        </span>
      )}
    </div>
  );
}
