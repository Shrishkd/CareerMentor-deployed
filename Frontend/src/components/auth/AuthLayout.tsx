import { motion } from "framer-motion";
import { ReactNode } from "react";
import DarkModeToggle from "@/components/DarkModeToggle";

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
}

export const AuthLayout = ({ children, title, subtitle }: AuthLayoutProps) => {
  return (
    <div className="min-h-screen flex">
      {/* Theme Toggle */}
      <div className="fixed top-4 right-4 z-50">
        <DarkModeToggle />
      </div>
      
      {/* Left Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md space-y-8"
        >
          <div className="text-center">
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-4xl font-bold bg-gradient-primary bg-clip-text text-transparent"
            >
              {title}
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-muted-foreground mt-2"
            >
              {subtitle}
            </motion.p>
          </div>
          {children}
        </motion.div>
      </div>

      {/* Right Side - Hero */}
      <div className="hidden lg:flex lg:flex-1 bg-gradient-hero items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="text-center text-primary-foreground"
        >
          <motion.div
            animate={{ 
              rotate: [0, 5, -5, 0],
              scale: [1, 1.05, 0.95, 1]
            }}
            transition={{ 
              duration: 6,
              repeat: Infinity,
              repeatType: "reverse"
            }}
            className="w-64 h-64 mx-auto mb-8 bg-gradient-card rounded-full flex items-center justify-center backdrop-blur-sm"
          >
            <div className="w-48 h-48 bg-primary-foreground rounded-full flex items-center justify-center">
              <span className="text-6xl">🎯</span>
            </div>
          </motion.div>
          <h2 className="text-3xl font-bold mb-4">AI-Powered Interviews</h2>
          <p className="text-lg opacity-90">
            Experience the future of hiring with our advanced gesture analysis and 
            intelligent question generation system.
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default AuthLayout;