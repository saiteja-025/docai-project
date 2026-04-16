import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LayoutDashboard, FileText, MessageSquare, BrainCircuit, Settings, Sun, Moon, LogOut } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function Sidebar({ isDark, toggleDark }) {
  const location = useLocation();


  const navItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Documents', path: '/documents', icon: <FileText size={20} /> },
    { name: 'Chat', path: '/chat', icon: <MessageSquare size={20} /> },
    { name: 'Quizzes', path: '/quizzes', icon: <BrainCircuit size={20} /> },
    { name: 'Settings', path: '/settings', icon: <Settings size={20} /> },
  ];

  const handleLogout = () => {
    localStorage.removeItem('docToken');
    localStorage.removeItem('recentQuizScores');
    window.location.href = '/';
  };

  return (
    <div className="w-64 border-r border-border bg-card/80 backdrop-blur-xl h-full flex flex-col pt-8 pb-4 transition-colors duration-300 shadow-[4px_0_24px_-10px_rgba(0,0,0,0.1)] dark:shadow-[4px_0_24px_-10px_rgba(0,0,0,0.5)] z-50">
      <div className="px-6 mb-10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <BrainCircuit className="text-white" size={20} />
        </div>
        <span className="font-bold text-xl tracking-tight text-foreground">DocIntell</span>
      </div>
      
      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <Link key={item.name} to={item.path} className="relative block">
              {isActive && (
                <motion.div
                  layoutId="active-nav-bg"
                  className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded-xl"
                  initial={false}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                />
              )}
              <div className={cn(
                "relative flex items-center gap-3 px-4 py-3 rounded-xl transition-colors z-10",
                isActive 
                  ? "text-blue-700 dark:text-blue-400 font-semibold" 
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}>
                {item.icon}
                <span>{item.name}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 mt-auto space-y-2">
        <button 
          onClick={toggleDark}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-muted-foreground hover:bg-muted/50 transition-colors hover:text-foreground font-medium"
        >
          {isDark ? <Sun size={20} className="text-amber-500" /> : <Moon size={20} className="text-blue-400" />}
          <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors font-medium group"
        >
          <LogOut size={20} className="group-hover:-translate-x-0.5 transition-transform" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
}
