import { useEffect } from 'react';
import { FileDropZone } from '../components/ui/file-drop-zone';
import { FileCard } from '../components/ui/file-card';
import { useFileStore } from '../stores/fileStore';
import { useTaskStore } from '../stores/taskStore';
import { Spinner } from '../components/ui/spinner';

export function Dashboard() {
  const { files, selectedFileId, addFiles, selectFile, loadFiles, isLoading } = useFileStore();
  const { tasks, loadTaskStatus, retryTask } = useTaskStore();

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  useEffect(() => {
    files.forEach((file) => {
      if (!tasks[file.id]) {
        loadTaskStatus(file.id);
      }
    });
  }, [files, tasks, loadTaskStatus]);

  const handleFilesSelected = async (newFiles: File[]) => {
    try {
      await addFiles(newFiles);
    } catch (error) {
      console.error('Failed to upload files:', error);
      alert('Failed to upload files. Please try again.');
    }
  };

  const handleRetryTask = async (fileId: string, taskType: string) => {
    try {
      await retryTask(fileId, taskType as any);
    } catch (error) {
      console.error('Failed to retry task:', error);
      alert('Failed to retry task. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">PDFTranslator</h1>
          <p className="mt-2 text-gray-600">Document Workflow Dashboard</p>
        </div>

        <div className="mb-8">
          <FileDropZone onFilesSelected={handleFilesSelected} />
        </div>

        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Files ({files.length})
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {files.map((file) => (
            <FileCard
              key={file.id}
              file={file}
              taskStatus={tasks[file.id]}
              isSelected={selectedFileId === file.id}
              onClick={() => selectFile(file.id)}
              onRetryTask={(taskType) => handleRetryTask(file.id, taskType)}
            />
          ))}
        </div>

        {files.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No files uploaded yet. Drop files above to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
