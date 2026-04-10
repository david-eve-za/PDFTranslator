import { Outlet, Link, useParams } from 'react-router-dom';
import { useFileStore } from '../stores/fileStore';

export function TaskLayout() {
  const { fileId } = useParams<{ fileId: string }>();
  const { files } = useFileStore();
  const file = files.find((f) => f.id === fileId);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link to="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Dashboard
          </Link>
          {file && (
            <h1 className="text-2xl font-bold text-gray-900 mt-4">
              {file.name}
            </h1>
          )}
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </div>
    </div>
  );
}
