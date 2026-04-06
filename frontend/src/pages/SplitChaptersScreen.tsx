import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '../components/ui/card';
import type { Chapter } from '../types';
import { chapterApi } from '../services/api';

export function SplitChaptersScreen() {
  const { fileId } = useParams<{ fileId: string }>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!fileId) return;

    const loadChapters = async () => {
      try {
        const data = await chapterApi.list(fileId);
        setChapters(data);
      } catch (error) {
        console.error('Failed to load chapters:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadChapters();
  }, [fileId]);

  if (isLoading) {
    return <div className="text-center py-12">Loading chapters...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          Chapter Breakdown ({chapters.length} chapters detected)
        </h2>
      </div>

      <div className="space-y-4">
        {chapters.map((chapter) => (
          <Card key={chapter.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{chapter.title}</h3>
                <p className="text-sm text-gray-500">
                  Chapter {chapter.chapterNumber}
                </p>
              </div>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Preview
                </button>
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Edit Title
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-6 flex space-x-4">
        <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
          Run Auto-Detection Again
        </button>
        <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Approve & Continue
        </button>
      </div>
    </div>
  );
}
