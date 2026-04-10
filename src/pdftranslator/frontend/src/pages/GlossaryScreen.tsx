import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import type { GlossaryEntry } from '../types';
import { glossaryApi } from '../services/api';

export function GlossaryScreen() {
  const { fileId } = useParams<{ fileId: string }>();
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!fileId) return;

    const loadGlossary = async () => {
      try {
        const data = await glossaryApi.list(fileId);
        setEntries(data);
      } catch (error) {
        console.error('Failed to load glossary:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadGlossary();
  }, [fileId]);

  const handleSearch = async () => {
    if (!fileId || !searchQuery) return;

    try {
      const data = await glossaryApi.search(fileId, searchQuery);
      setEntries(data);
    } catch (error) {
      console.error('Failed to search glossary:', error);
    }
  };

  const filteredEntries = searchQuery
    ? entries.filter(
        (e) =>
          e.sourceTerm.includes(searchQuery) || e.targetTerm.includes(searchQuery)
      )
    : entries;

  if (isLoading) {
    return <div className="text-center py-12">Loading glossary...</div>;
  }

  return (
    <div>
      <div className="mb-6 flex space-x-4">
        <Input
          type="text"
          placeholder="Search terms..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Search
        </button>
        <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
          Add Term
        </button>
      </div>

      <div className="space-y-4">
        {filteredEntries.map((entry) => (
          <Card key={entry.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-gray-900">{entry.sourceTerm}</div>
                <div className="text-blue-600 mt-1">→ {entry.targetTerm}</div>
                {entry.context && (
                  <div className="text-sm text-gray-500 mt-2">
                    Context: "{entry.context}"
                  </div>
                )}
              </div>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">
                  Edit
                </button>
                <button className="px-3 py-1 text-sm text-red-600 hover:text-red-800">
                  Delete
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filteredEntries.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No glossary entries found.
        </div>
      )}
    </div>
  );
}
