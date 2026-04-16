import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Mail, Lock, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function Auth({ setToken }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      if (isLogin) {
        // Login Request
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        
        const token = response.data.access_token;
        localStorage.setItem('docToken', token);
        setToken(token);
      } else {
        // Signup Request
        await axios.post(`${API_BASE_URL}/auth/signup`, { password, email });
        setIsLogin(true); // Automatically switch to login
        setSuccessMsg('Account created successfully! Please sign in with your new credentials.');
        setPassword(''); // Clear password for security
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAuthMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setSuccessMsg('');
    setPassword('');
  };

  return (
    <div className="min-h-screen w-full flex bg-background text-foreground transition-colors duration-300">
      
      {/* Left Panel - Premium Brand Hero (Hidden on Mobile) */}
      <div className="hidden lg:flex w-[55%] relative overflow-hidden bg-slate-900 items-center justify-center p-12">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-700 via-indigo-900 to-purple-950" />
        {/* Abstract shapes */}
        <div className="absolute top-[-20%] left-[-10%] w-[70%] h-[70%] bg-blue-500/20 blur-[120px] rounded-full mix-blend-overlay" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-500/30 blur-[100px] rounded-full mix-blend-overlay" />
        
        <div className="relative z-10 text-white max-w-lg">
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <div className="w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center mb-8 shadow-2xl">
              <BrainCircuit size={32} className="text-white" />
            </div>
            <h1 className="text-5xl font-extrabold tracking-tight mb-6 leading-tight">
              Unlock the Intelligence Inside Your Documents.
            </h1>
            <p className="text-lg text-slate-300 font-medium mb-12 max-w-md leading-relaxed">
              Upload complex PDFs and let our RAG-powered engine instantly chat with you. Elevate your productivity in seconds.
            </p>
            
            <div className="space-y-4">
              {[
                "Context-aware chat powered by Groq",
                "Automatic intelligent parsing",
                "Advanced vector semantic search"
              ].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
                    <CheckCircle2 size={14} className="text-white" />
                  </div>
                  <span className="text-slate-100 font-medium">{feature}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Panel - Auth Form */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-8 sm:p-12 lg:p-24 relative bg-card dark:bg-slate-900 transition-colors duration-300 border-l border-border">
        <div className="w-full max-w-md relative z-10">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-12">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
              <BrainCircuit className="text-white" size={24} />
            </div>
            <span className="font-bold text-2xl tracking-tight text-foreground">DocIntell</span>
          </div>

          <motion.div
            key={isLogin ? 'login' : 'signup'}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h2 className="text-3xl font-bold tracking-tight mb-2 text-foreground">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="text-muted-foreground mb-8">
              {isLogin 
                ? 'Enter your email and password to access your workspace.' 
                : 'Enter your details below to create your account and get started.'}
            </p>

            <AnimatePresence mode="wait">
              {successMsg && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-400 text-sm font-medium flex items-center gap-2"
                >
                  <CheckCircle2 size={16} className="shrink-0" />
                  {successMsg}
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-foreground/90">Email address</label>
                <div className="relative group">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-blue-500 transition-colors" size={18} />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-background border-2 border-border/50 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-blue-500 focus:ring-0 transition-all font-medium text-foreground placeholder:text-muted-foreground"
                    placeholder="name@example.com"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-foreground/90">Password</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-blue-500 transition-colors" size={18} />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-background border-2 border-border/50 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-blue-500 focus:ring-0 transition-all font-medium text-foreground placeholder:text-muted-foreground"
                    placeholder="••••••••"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              <AnimatePresence mode="wait">
                {error && (
                  <motion.p 
                    initial={{ opacity: 0, height: 0 }} 
                    animate={{ opacity: 1, height: 'auto' }} 
                    exit={{ opacity: 0, height: 0 }}
                    className="text-sm text-red-600 dark:text-red-400 font-medium bg-red-500/10 p-3 rounded-lg border border-red-500/20"
                  >
                    {error}
                  </motion.p>
                )}
              </AnimatePresence>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-3.5 font-bold shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none mt-4"
              >
                {isLoading ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <>
                    {isLogin ? 'Sign In' : 'Sign Up'}
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-8 text-center text-sm text-muted-foreground font-medium flex items-center justify-center gap-1">
              {isLogin ? "Don't have an account?" : "Already have an account?"}
              <button 
                type="button"
                onClick={toggleAuthMode}
                className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none"
              >
                {isLogin ? 'Sign up' : 'Sign in'}
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
