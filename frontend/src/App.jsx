import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { BrainCircuit } from 'lucide-react';

import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import Chat from './pages/Chat';
import Sidebar from './components/Sidebar';

import Quizzes from './pages/Quizzes';

export default function App() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('docThemeIsDark');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [token, setToken] = useState(localStorage.getItem('docToken'));

  useEffect(() => {
    localStorage.setItem('docThemeIsDark', JSON.stringify(isDark));
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  if (!token) {
    return <Auth setToken={setToken} />;
  }

  return (
    <Router>
      <div className="flex h-screen overflow-hidden bg-background text-foreground transition-colors duration-300">
        <Sidebar isDark={isDark} toggleDark={() => setIsDark(!isDark)} />
        <main className="flex-1 overflow-auto relative">
          
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/quizzes" element={<Quizzes />} />

              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </Router>
  );
}
