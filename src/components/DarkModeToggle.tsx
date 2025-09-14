import React, { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

interface DarkModeToggleProps {
  className?: string;
}

const DarkModeToggle: React.FC<DarkModeToggleProps> = ({ className = '' }) => {
  const [isDark, setIsDark] = useState(false);

  // Check for saved theme preference or default to light mode
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      setIsDark(true);
    }
  };

  return (
    <button
      onClick={toggleDarkMode}
      className={`relative inline-flex h-10 w-18 items-center justify-center rounded-full 
        bg-gradient-to-r from-orange-400 to-purple-500 p-1 transition-all duration-300 
        hover:shadow-lg hover:scale-105 ${className}`}
      aria-label="Toggle dark mode"
    >
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full bg-white 
          shadow-md transition-all duration-300 ${
            isDark ? 'translate-x-4' : 'translate-x-0'
          }`}
      >
        {isDark ? (
          <Moon className="h-4 w-4 text-slate-700" />
        ) : (
          <Sun className="h-4 w-4 text-orange-500" />
        )}
      </div>
    </button>
  );
};

export default DarkModeToggle;
