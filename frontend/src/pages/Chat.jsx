import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, FileText, Bot, User as UserIcon, Loader2, MessageSquareOff, Trash2 } from 'lucide-react';
import axios from 'axios';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function Chat() {
  const location = useLocation();
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(location.state?.selectedDocId || null);
  const [messagesCache, setMessagesCache] = useState({});
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const messagesEndRef = useRef(null);

  // Fetch docs on mount
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = localStorage.getItem('docToken');
        const res = await axios.get(`${API_BASE_URL}/documents/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Filter only ready documents
        setDocuments(res.data.filter(d => d.status === 'ready'));
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingDocs(false);
      }
    };
    fetchDocs();
  }, []);

  // Fetch history when doc changes
  useEffect(() => {
    if (!selectedDocId) return;
    
    // Load from cache instantly if available to prevent flicker
    if (messagesCache[selectedDocId]) {
       setMessages(messagesCache[selectedDocId]);
    } else {
       setMessages([]);
    }
    
    const fetchHistory = async () => {
      try {
        const token = localStorage.getItem('docToken');
        const res = await axios.get(`${API_BASE_URL}/chat/${selectedDocId}/history`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setMessages(res.data);
        setMessagesCache(prev => ({ ...prev, [selectedDocId]: res.data }));
      } catch (err) {
        console.error(err);
      }
    };
    fetchHistory();
    // Also clear input 
    setInput('');
  }, [selectedDocId]);

  useEffect(() => {
    if (location.state?.selectedDocId) {
       setSelectedDocId(location.state.selectedDocId);
    }
  }, [location.state]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleDelete = async (e, docId) => {
    e.stopPropagation();
    
    try {
      const token = localStorage.getItem('docToken');
      await axios.delete(`${API_BASE_URL}/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to delete document", err);
      alert("Failed to delete document.");
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !selectedDocId || isSending) return;

    const userMessage = input.trim();
    setInput('');
    const userMsgObj = { role: 'user', content: userMessage };
    setMessages(prev => [...prev, userMsgObj]);
    setMessagesCache(prev => ({ ...prev, [selectedDocId]: [...(prev[selectedDocId] || []), userMsgObj] }));
    setIsSending(true);

    try {
      const token = localStorage.getItem('docToken');
      const res = await axios.post(`${API_BASE_URL}/chat/${selectedDocId}/chat`, 
        { query: userMessage },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const aiMsgObj = { role: 'ai', content: res.data.reply };
      setMessages(prev => [...prev, aiMsgObj]);
      setMessagesCache(prev => ({ ...prev, [selectedDocId]: [...(prev[selectedDocId] || []), aiMsgObj] }));
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'ai', content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-full w-full bg-background overflow-hidden relative">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] rounded-full bg-blue-500/10 blur-[150px] pointer-events-none" />

      {/* Docs Sidebar */}
      <div className="w-80 border-r border-border bg-card/40 backdrop-blur-md flex flex-col z-10 transition-colors">
        <div className="p-6 border-b border-border">
          <h2 className="font-bold text-lg text-foreground flex items-center gap-2">
            <FileText size={20} className="text-blue-500" />
            Knowledge Base
          </h2>
          <p className="text-xs text-muted-foreground mt-1">Select a document to begin chatting</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isLoadingDocs ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-blue-500" /></div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 px-4 text-sm text-muted-foreground bg-muted/30 rounded-xl border border-dashed border-border">
              No ready documents found. Go to Documents to upload PDFs.
            </div>
          ) : (
            documents.map(doc => (
              <div
                key={doc.id}
                className={cn(
                  "w-full flex items-center justify-between p-2 pr-3 rounded-xl border transition-all text-sm font-medium",
                  selectedDocId === doc.id
                    ? "bg-blue-600 border-blue-500 text-white shadow-md shadow-blue-500/20"
                    : "bg-background border-border text-foreground hover:border-blue-500/50 hover:bg-card"
                )}
              >
                <button
                  onClick={() => setSelectedDocId(doc.id)}
                  className="text-left flex-1 pl-2 py-2"
                >
                  <div className="line-clamp-2">{doc.title}</div>
                  <div className={cn(
                    "text-[10px] mt-1 font-medium uppercase tracking-wider",
                    selectedDocId === doc.id ? "text-blue-100" : "text-muted-foreground"
                  )}>
                    Ready for Chat
                  </div>
                </button>
                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  className={cn(
                    "shrink-0 p-2 rounded-lg transition-colors ml-2",
                    selectedDocId === doc.id 
                      ? "hover:bg-white/20 text-white/80 hover:text-white"
                      : "hover:bg-red-500/10 text-muted-foreground hover:text-red-500"
                  )}
                  title="Delete Document"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col relative z-10">
        {!selectedDocId ? (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <MessageSquareOff size={64} className="mb-4 opacity-20" />
            <h3 className="text-xl font-semibold mb-2 text-foreground">No Document Selected</h3>
            <p>Select a document from the left panel to start a conversation.</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="px-8 py-5 border-b border-border bg-background/50 backdrop-blur-md flex items-center shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                  <Bot size={20} className="text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-bold text-foreground line-clamp-1 max-w-md">
                    {documents.find(d => d.id === selectedDocId)?.title}
                  </h3>
                  <div className="flex items-center gap-1.5 object-contain">
                     <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
                     <span className="text-xs text-muted-foreground font-medium">AI Agent Online</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center opacity-70">
                  <Bot size={48} className="text-blue-500/50 mb-4" />
                  <p className="text-muted-foreground font-medium">Hello! Ask me anything about this document.</p>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      "flex w-full",
                      msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                  >
                    <div className={cn(
                      "flex max-w-[80%] gap-4",
                      msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                    )}>
                      {/* Avatar */}
                      <div className={cn(
                        "w-10 h-10 shrink-0 rounded-2xl flex items-center justify-center mt-1 shadow-sm border",
                        msg.role === 'user' 
                          ? "bg-foreground text-background border-foreground" 
                          : "bg-card border-border text-blue-500"
                      )}>
                        {msg.role === 'user' ? <UserIcon size={18} /> : <Bot size={20} />}
                      </div>

                      {/* Bubble */}
                      <div className={cn(
                        "p-4 rounded-2xl text-sm leading-relaxed shadow-sm",
                        msg.role === 'user'
                          ? "bg-blue-600 text-white rounded-tr-sm"
                          : "bg-card border border-border text-foreground rounded-tl-sm dark:bg-slate-800"
                      )}>
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}

              {/* Typing indicator */}
              <AnimatePresence>
                {isSending && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="flex w-full justify-start"
                  >
                    <div className="flex gap-4">
                      <div className="w-10 h-10 shrink-0 rounded-2xl flex items-center justify-center mt-1 shadow-sm border bg-card border-border text-blue-500">
                        <Bot size={20} />
                      </div>
                      <div className="p-5 rounded-2xl bg-card border border-border rounded-tl-sm text-foreground flex items-center gap-1.5 shadow-sm">
                        <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0 }} className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                        <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }} className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                        <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }} className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div className="p-4 sm:p-6 bg-background/80 backdrop-blur-md border-t border-border">
              <form onSubmit={handleSend} className="max-w-4xl mx-auto relative flex items-end gap-3 group">
                <div className="flex-1 relative bg-card overflow-hidden rounded-2xl border-2 border-border focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-500/10 transition-all shadow-sm">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend(e);
                      }
                    }}
                    placeholder="Ask a question about your document..."
                    className="w-full max-h-32 min-h-[60px] bg-transparent resize-none py-4 px-5 focus:outline-none text-sm text-foreground placeholder:text-muted-foreground font-medium"
                    rows={1}
                  />
                </div>
                <button
                  type="submit"
                  disabled={!input.trim() || isSending}
                  className="shrink-0 h-[60px] w-[60px] flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md shadow-blue-500/20 active:scale-95"
                >
                  <Send size={24} className="translate-x-[-1px] translate-y-[1px]" />
                </button>
              </form>
              <div className="text-center mt-3 text-xs text-muted-foreground font-medium">
                AI responses may be inaccurate. Double-check core facts.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
