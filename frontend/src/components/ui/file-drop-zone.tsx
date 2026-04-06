import React, { useCallback, useState } from 'react';
import { Card } from './card';

interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes?: string[];
}

const ACCEPTED_TYPES = ['.pdf', '.epub', '.doc', '.docx'];

export function FileDropZone({ onFilesSelected, acceptedTypes = ACCEPTED_TYPES }: FileDropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);

  const validateFiles = useCallback((files: FileList | null): File[] => {
    if (!files) return [];

    const validFiles: File[] = [];
    const errors: string[] = [];

    Array.from(files).forEach((file) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (acceptedTypes.includes(ext)) {
        validFiles.push(file);
      } else {
        errors.push(`${file.name} has invalid type. Allowed: ${acceptedTypes.join(', ')}`);
      }
    });

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    return validFiles;
  }, [acceptedTypes]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(false);
    const validFiles = validateFiles(e.dataTransfer.files);
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [validateFiles, onFilesSelected]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const validFiles = validateFiles(e.target.files);
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [validateFiles, onFilesSelected]);

  return (
    <Card
      className={`p-12 border-2 border-dashed cursor-pointer transition-all relative ${
        isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="flex flex-col items-center justify-center space-y-4">
        <svg
          className={`w-12 h-12 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="text-lg font-medium text-gray-700">
          Drop PDF, EPUB, DOC, or DOCX files here
        </p>
        <p className="text-sm text-gray-500">or click to browse</p>
        <input
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </Card>
  );
}
