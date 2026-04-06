# PDFTranslator Frontend

React-based web UI for PDFTranslator document processing workflow.

## Tech Stack

- React 18 + TypeScript (strict mode)
- Vite (build tool)
- Zustand (state management)
- shadcn/ui (component library)
- Tailwind CSS
- React Router (routing)

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npx tsc --noEmit
```

## Environment Variables

Create `.env` file:

```
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:8000/api
```

## Project Structure

```
src/
├── components/
│   ├── containers/    # Logic-heavy components
│   └── ui/            # Presentational components (shadcn/ui)
├── pages/             # Route pages
├── stores/            # Zustand state stores
├── services/          # API abstraction layer
├── hooks/             # Custom React hooks
├── types/             # TypeScript types
└── lib/               # Utilities
```

## Features

- File upload (drag & drop + manual selection)
- File type validation (PDF, EPUB, DOC, DOCX)
- Task status tracking (pending, in-progress, completed, failed)
- Split Chapters screen
- Glossary screen with search/filter
- Translated screen (side-by-side view)
- Audio screen with player

## Testing

```bash
# Run tests (TODO: add test setup)
npm test
```

## Notes

- Mock data enabled by default (set `VITE_USE_MOCK_DATA=false` to use real API)
- Backend API must be running on http://localhost:8000
- TypeScript strict mode enabled
