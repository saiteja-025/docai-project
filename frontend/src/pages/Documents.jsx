import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, UploadCloud, Loader2, CheckCircle2, AlertCircle, Trash2, Eye, Download, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [activeDetailDoc, setActiveDetailDoc] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const fetchDocuments = async () => {
    try {
      const token = localStorage.getItem('docToken');
      const res = await axios.get(`${API_BASE_URL}/documents/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(res.data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Poll every 10s if any doc is 'processing'
    const interval = setInterval(() => {
      setDocuments((currentDocs) => {
        if (currentDocs.some(d => d.status === 'processing')) {
          fetchDocuments();
        }
        return currentDocs;
      });
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async (file) => {
    if (!file) return;
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.docx') && !lowerName.endsWith('.txt')) {
      alert("Please upload a PDF, DOCX, or TXT file.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      alert("File size exceeds 25 MB. Please select a smaller file.");
      return;
    }

    setIsUploading(true);
    const token = localStorage.getItem('docToken');
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API_BASE_URL}/documents/upload`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      fetchDocuments();
    } catch (err) {
      console.error("Upload failed", err);
      alert(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const onDragLeave = () => setIsDragging(false);
  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleUpload(file);
  };

  const handleDelete = async (e, docId) => {
    e.stopPropagation();
    e.preventDefault();

    if (!window.confirm("Are you sure you want to delete this document? All associated chats and quizzes will also be deleted.")) {
      return;
    }
    
    try {
      const token = localStorage.getItem('docToken');
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (activeDetailDoc?.id === docId) setActiveDetailDoc(null);
      
      await axios.delete(`${API_BASE_URL}/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchDocuments();
    } catch (err) {
      console.error("Failed to delete document", err);
      alert("Failed to delete document.");
      fetchDocuments();
    }
  };

  const cleanText = (val) => {
    if (!val) return null;
    try {
      const parsed = JSON.parse(val);
      if (typeof parsed === 'string') return parsed;
      return JSON.stringify(parsed, null, 2);
    } catch {
      return val;
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-8 max-w-7xl mx-auto pb-32 space-y-12">
      <header>
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">Documents</h1>
        <p className="text-muted-foreground mt-2 text-lg">Upload and manage your intelligence repository.</p>
      </header>

      {/* Uploader */}
      <div 
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`border-2 ${isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-dashed border-border bg-card/50'} rounded-3xl p-16 flex flex-col items-center justify-center text-center transition-all duration-300 relative overflow-hidden group`}
      >
        <input 
          type="file" 
          accept=".pdf,.docx,.txt"
          ref={fileInputRef}
          onChange={(e) => handleUpload(e.target.files[0])}
          className="hidden" 
        />
        
        {isUploading ? (
          <div className="flex flex-col items-center min-h-[140px] justify-center">
            <Loader2 size={48} className="text-blue-500 animate-spin mb-4" />
            <h3 className="text-xl font-semibold mb-2">Analyzing Document...</h3>
            <p className="text-muted-foreground">Extracting text and generating embeddings. This might take a moment.</p>
          </div>
        ) : (
          <div className="flex flex-col items-center min-h-[140px] justify-center">
            <div className="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-blue-500/20 transition-all duration-300">
              <UploadCloud className="text-blue-600 dark:text-blue-400" size={36} />
            </div>
            <h3 className="text-2xl font-bold mb-3 text-foreground">Click or drag a file here</h3>
            <p className="text-muted-foreground max-w-md text-base">Support for PDF, DOCX, and TXT files up to 25 MB. Let our AI unlock insights, generate flashcards, and prepare conversational contexts.</p>
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="mt-8 bg-foreground hover:bg-foreground/90 text-background px-8 py-3 rounded-xl font-bold active:scale-95 transition-all shadow-lg shadow-black/10"
            >
              Select File
            </button>
          </div>
        )}
      </div>

      {/* List */}
      <div>
        <h2 className="text-2xl font-bold mb-6 text-foreground flex items-center gap-3">
          Your Repository
          <span className="bg-blue-500/10 text-blue-600 dark:text-blue-400 text-sm py-1 px-3 rounded-full font-semibold">
            {documents.length} Files
          </span>
        </h2>
        
        {isLoadingList ? (
          <div className="flex justify-center p-12">
            <Loader2 className="animate-spin text-blue-500" size={32} />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center p-12 border border-border rounded-2xl bg-card/30">
            <FileText className="mx-auto text-muted-foreground/30 mb-4" size={48} />
            <p className="text-muted-foreground font-medium">No documents uploaded yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {documents.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ delay: i * 0.05 }}
                  className="bg-card dark:bg-card/50 border border-border rounded-2xl p-6 hover:shadow-md hover:border-blue-500/30 transition-all flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-start justify-between mb-4">
                      <div className="p-3 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-colors">
                        <FileText className="text-blue-600 dark:text-blue-400" size={24} />
                      </div>
                      
                      {doc.status === 'processing' && (
                        <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-600 bg-amber-500/10 px-2.5 py-1 rounded-md">
                          <Loader2 size={12} className="animate-spin" /> Processing
                        </span>
                      )}
                      {doc.status === 'ready' && (
                        <span className="flex items-center gap-1.5 text-xs font-semibold text-green-600 bg-green-500/10 px-2.5 py-1 rounded-md">
                          <CheckCircle2 size={12} /> Ready
                        </span>
                      )}
                      {doc.status === 'failed' && (
                        <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600 bg-red-500/10 px-2.5 py-1 rounded-md">
                          <AlertCircle size={12} /> Failed
                        </span>
                      )}
                    </div>
                    <h4 className="font-bold text-lg text-foreground line-clamp-2" title={doc.title}>
                      {doc.title}
                    </h4>
                    <p className="text-xs text-muted-foreground mt-2">
                      Uploaded on {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                    {doc.summary_short && (
                      <p className="text-xs text-muted-foreground/80 mt-2 line-clamp-2 italic">
                        &ldquo;{cleanText(doc.summary_short)}&rdquo;
                      </p>
                    )}
                  </div>
                  
                  <div className="mt-6 flex items-center gap-2">
                    <button 
                      disabled={doc.status !== 'ready'}
                      className="flex-1 bg-secondary text-secondary-foreground hover:bg-secondary/80 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => navigate('/chat', { state: { selectedDocId: doc.id } })}
                    >
                      Chat
                    </button>
                    <button 
                      onClick={() => setActiveDetailDoc(doc)}
                      className="p-2 bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20 rounded-lg transition-colors"
                      title="View Summary & Details"
                    >
                      <Eye size={16} />
                    </button>
                    {doc.cloudinary_url && doc.cloudinary_url.startsWith('http') && (
                      <a
                        href={doc.cloudinary_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 rounded-lg transition-colors"
                        title="Download Document"
                      >
                        <Download size={16} />
                      </a>
                    )}
                    <button 
                      onClick={(e) => handleDelete(e, doc.id)}
                      className="p-2 bg-red-500/5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete Document"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Details & Summary Modal */}
      <AnimatePresence>
        {activeDetailDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-card border border-border rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl"
            >
              <div className="p-6 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500">
                    <FileText size={20} />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-foreground line-clamp-1">{activeDetailDoc.title}</h3>
                    <p className="text-xs text-muted-foreground">Uploaded {new Date(activeDetailDoc.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveDetailDoc(null)}
                  className="p-2 text-muted-foreground hover:text-foreground rounded-lg"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-6">
                <div>
                  <h4 className="text-xs uppercase tracking-wider font-bold text-muted-foreground mb-2">Short Summary</h4>
                  <div className="p-4 rounded-xl bg-background border border-border text-sm leading-relaxed text-foreground">
                    {cleanText(activeDetailDoc.summary_short) || "Summary being generated by AI..."}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs uppercase tracking-wider font-bold text-muted-foreground mb-2">Detailed Insights</h4>
                  <div className="p-4 rounded-xl bg-background border border-border text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                    {cleanText(activeDetailDoc.summary_detailed) || "Detailed analysis will appear once processed."}
                  </div>
                </div>

                {activeDetailDoc.cloudinary_url && activeDetailDoc.cloudinary_url.startsWith('http') && (
                  <div className="pt-2">
                    <a
                      href={activeDetailDoc.cloudinary_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition-colors"
                    >
                      <Download size={16} /> Download Original File
                    </a>
                  </div>
                )}
              </div>

              <div className="p-4 border-t border-border bg-card/50 flex justify-end gap-2">
                <button
                  onClick={() => {
                    const id = activeDetailDoc.id;
                    setActiveDetailDoc(null);
                    navigate('/chat', { state: { selectedDocId: id } });
                  }}
                  className="px-4 py-2 bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-xl text-sm font-semibold transition-colors"
                >
                  Open Chat
                </button>
                <button
                  onClick={() => setActiveDetailDoc(null)}
                  className="px-4 py-2 bg-foreground text-background rounded-xl text-sm font-semibold transition-colors"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
