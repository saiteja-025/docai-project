import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Activity, BrainCircuit, TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const StatCard = ({ icon: Icon, label, value, delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay }}
    className="bg-card/40 backdrop-blur-xl rounded-[1.5rem] p-6 border border-border/50 flex items-center gap-5 hover:border-blue-500/50 hover:bg-card/60 transition-all shadow-[0_4px_20px_rgb(0,0,0,0.02)] group"
  >
    <div className="p-4 bg-blue-500/10 text-blue-500 rounded-2xl group-hover:scale-110 transition-transform duration-300">
      <Icon size={28} />
    </div>
    <div>
      <h4 className="text-3xl font-extrabold text-foreground tracking-tight">{value}</h4>
      <p className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mt-1">{label}</p>
    </div>
  </motion.div>
);

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('docToken');
        if (!token) return;
        const res = await axios.get(`${API_BASE_URL}/dashboard/stats`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setStats(res.data);
        
        try {
           const docsRes = await axios.get(`${API_BASE_URL}/documents/`, {
              headers: { Authorization: `Bearer ${token}` }
           });
           setDocuments(docsRes.data);
        } catch (e) { console.error("Docs load failed", e); }
      } catch (err) {
        console.error("Failed to fetch dashboard stats", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="relative h-full w-full bg-background overflow-hidden flex flex-col">
      {/* Background Ambient Gradients */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-500/10 blur-[120px] mix-blend-screen" />
        <div className="absolute top-[40%] right-[-10%] w-[40%] h-[60%] rounded-full bg-purple-500/10 blur-[150px] mix-blend-screen" />
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto p-8 md:p-12 lg:px-16 w-full max-w-[1600px] mx-auto space-y-10">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, ease: "easeOut" }}>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-foreground to-foreground/70">
              Welcome back
            </h1>
            <p className="text-muted-foreground mt-3 text-lg max-w-xl leading-relaxed">
              Manage your documents and start chatting with your AI assistant.
            </p>
          </motion.div>
        </header>
        
        {/* Stats Grid */}
        {!isLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
             <StatCard icon={FileText} label="Documents" value={stats.doc_count || documents.length || 0} delay={0.1} />
             <StatCard icon={Activity} label="Chats" value={stats.chat_count || 0} delay={0.2} />
             <StatCard icon={BrainCircuit} label="Avg Score" value={stats.avg_score !== undefined && stats.avg_score !== null ? `${stats.avg_score}%` : '0%'} delay={0.3} />
             <StatCard icon={TrendingUp} label="Platform Rank" value={stats.avg_score > 0 ? (stats.avg_score >= 80 ? "A+" : stats.avg_score >= 50 ? "B" : "C") : 'N/A'} delay={0.4} />
          </div>
        )}

        {/* Main Content Layout */}
        <div className="flex flex-col gap-8">
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="w-full bg-card/60 backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-border/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden flex flex-col"
          >
            <div className="flex items-center justify-between z-10 relative mb-8 border-b border-border/40 pb-6">
               <h3 className="font-bold text-2xl text-foreground flex items-center gap-3">
                 <FileText className="text-blue-500" /> Recent Documents
               </h3>
               {documents.length > 0 && (
                 <span className="text-sm font-medium text-muted-foreground">Quick access to your latest files</span>
               )}
            </div>
            
            <div className="flex-1 w-full z-10">
               {isLoading ? (
                 <div className="w-full py-12 flex justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                 </div>
               ) : Array.isArray(documents) && documents.length > 0 ? (
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   {documents.slice(0, 6).map((doc, i) => (
                     <motion.div 
                       initial={{ opacity: 0, scale: 0.95 }}
                       animate={{ opacity: 1, scale: 1 }}
                       transition={{ duration: 0.4, delay: i * 0.05 }}
                       key={doc.id}
                       onClick={() => navigate('/chat', { state: { selectedDocId: doc.id } })}
                       className="p-5 rounded-2xl bg-background border border-border/60 hover:border-blue-500/50 hover:shadow-md cursor-pointer transition-all duration-300 group flex items-center justify-between"
                     >
                       <div className="flex items-center gap-4 overflow-hidden">
                          <div className="shrink-0 p-3 bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 rounded-xl group-hover:scale-110 transition-transform">
                            <FileText size={20} />
                          </div>
                          <div className="min-w-0 pr-4">
                             <h4 className="font-semibold text-foreground text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
                               {doc.title}
                             </h4>
                             <p className="text-xs text-muted-foreground mt-1 capitalize">
                               {doc.status}
                             </p>
                          </div>
                       </div>
                       <div className="shrink-0">
                          <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0">
                             &rarr;
                          </div>
                       </div>
                     </motion.div>
                   ))}
                 </div>
               ) : (
                 <div className="flex flex-col items-center justify-center py-16 text-muted-foreground opacity-70">
                   <div className="p-4 rounded-full bg-muted/50 mb-4">
                      <FileText size={40} />
                   </div>
                   <p className="text-lg font-medium">No documents uploaded yet</p>
                   <p className="text-sm mt-1">Upload your first document to get started</p>
                 </div>
               )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
