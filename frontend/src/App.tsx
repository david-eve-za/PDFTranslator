import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { TaskLayout } from './pages/TaskLayout';
import { SplitChaptersScreen } from './pages/SplitChaptersScreen';
import { GlossaryScreen } from './pages/GlossaryScreen';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/file/:fileId" element={<TaskLayout />}>
          <Route path="chapters" element={<SplitChaptersScreen />} />
          <Route path="glossary" element={<GlossaryScreen />} />
          <Route path="translated" element={<div>Translated Screen (TODO)</div>} />
          <Route path="audio" element={<div>Audio Screen (TODO)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
