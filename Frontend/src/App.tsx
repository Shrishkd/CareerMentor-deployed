import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./components/ThemeContext";
import DarkModeToggle from "./components/DarkModeToggle";

import Index from "./pages/Index";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Interview from "./pages/Interview";
import ATSChecker from "./pages/ATSChecker";
import ResumeUpload from "./pages/ResumeUpload";  // Added this import
import GrantPermissions from "./pages/GrantPermissions";  // Added this import
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          {/* Navigation bar with dark mode toggle */}
          <nav className="fixed top-4 right-4 z-50">
            <DarkModeToggle />
          </nav>

          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/resume-upload" element={<ResumeUpload />} />  {/* Added this route */}
            <Route path="/grant-permissions" element={<GrantPermissions />} />  {/* Added this route */}
            <Route path="/interview" element={<Interview />} />
            <Route path="/ats-checker" element={<ATSChecker />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
