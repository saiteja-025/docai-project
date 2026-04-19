import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function Quizzes() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [questions, setQuestions] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  
  // Quiz State
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [quizCache, setQuizCache] = useState({});

  useEffect(() => {
    if (selectedDocId) {
      setQuizCache(prev => ({
        ...prev,
        [selectedDocId]: { questions, answers, showResults, difficulty }
      }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questions, answers, showResults, difficulty, selectedDocId]);

  const handleSelectDoc = (docId) => {
    setSelectedDocId(docId);
    if (quizCache[docId]) {
       setQuestions(quizCache[docId].questions);
       setAnswers(quizCache[docId].answers);
       setShowResults(quizCache[docId].showResults);
       setDifficulty(quizCache[docId].difficulty || 'medium');
    } else {
       setQuestions(null);
       setAnswers({});
       setShowResults(false);
    }
  };

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const token = localStorage.getItem('docToken');
        const res = await axios.get(`${API_BASE_URL}/documents/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setDocuments(res.data.filter(d => d.status === 'ready'));
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingDocs(false);
      }
    };
    fetchDocs();
  }, []);

  const handleGenerateQuiz = async () => {
    if (!selectedDocId) return;
    setIsLoading(true);
    setQuestions(null);
    setAnswers({});
    setShowResults(false);
    
    try {
      const token = localStorage.getItem('docToken');
      const res = await axios.get(`${API_BASE_URL}/quiz/${selectedDocId}?difficulty=${difficulty}&t=${Date.now()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQuestions(res.data.questions);
    } catch (err) {
      console.error(err);
      alert('Failed to generate quiz.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectAnswer = (qIndex, option) => {
    if (showResults) return;
    setAnswers(prev => ({ ...prev, [qIndex]: option }));
  };

  const handleSubmit = async () => {
    if (Object.keys(answers).length < questions.length) {
      alert("Please answer all questions before submitting.");
      return;
    }
    setShowResults(true);
    
    // Persist score directly to sync with Dashboard overview
    const finalScore = calculateScore();
    try {
      const token = localStorage.getItem('docToken');
      await axios.post(`${API_BASE_URL}/quiz/submit`, 
        { score: finalScore, answers_json: JSON.stringify(answers) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (e) {
      console.error("Failed to save score to database", e);
    }
  };

  const calculateScore = () => {
    if (!questions) return 0;
    let score = 0;
    questions.forEach((q, i) => {
      if (answers[i] === q.correct_answer) score += 1;
    });
    return Math.round((score / questions.length) * 100);
  };

  return (
    <div className="flex h-full w-full bg-background overflow-hidden relative">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] rounded-full bg-purple-500/10 blur-[150px] pointer-events-none" />

      {/* Sidebar */}
      <div className="w-80 border-r border-border bg-card/40 backdrop-blur-md flex flex-col z-10">
        <div className="p-6 border-b border-border">
          <h2 className="font-bold text-lg text-foreground flex items-center gap-2">
            <BrainCircuit size={20} className="text-purple-500" />
            Quiz Engine
          </h2>
          <p className="text-xs text-muted-foreground mt-1">Select a document to test your knowledge.</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isLoadingDocs ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-purple-500" /></div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 px-4 text-sm text-muted-foreground bg-muted/30 rounded-xl border border-dashed">
              No ready documents found.
            </div>
          ) : (
            documents.map(doc => (
              <button
                key={doc.id}
                onClick={() => handleSelectDoc(doc.id)}
                className={cn(
                  "w-full text-left p-4 rounded-xl border transition-all text-sm font-medium",
                  selectedDocId === doc.id
                    ? "bg-purple-600 border-purple-500 text-white shadow-md shadow-purple-500/20"
                    : "bg-background border-border text-foreground hover:border-purple-500/50 hover:bg-card"
                )}
              >
                <div className="line-clamp-2">{doc.title}</div>
              </button>
            ))
          )}
        </div>
        
        <div className="p-4 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">Select a document, then use the main panel to start your quiz.</p>
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex flex-col relative z-10 overflow-y-auto p-8">
        {!questions && !isLoading && (
          <div className="h-full flex flex-col justify-center items-center text-center">
            <BrainCircuit size={64} className="text-purple-500/50 mb-6" />
            
            {!selectedDocId ? (
              <div className="opacity-70">
                <h2 className="text-2xl font-bold text-foreground mb-2">Ready to test your knowledge?</h2>
                <p className="text-muted-foreground max-w-md">Select a document from the sidebar to begin.</p>
              </div>
            ) : (
              <motion.div initial={{opacity: 0, scale: 0.95}} animate={{opacity: 1, scale: 1}} className="max-w-md w-full bg-card p-8 rounded-3xl border border-border/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
                <h2 className="text-2xl font-bold text-foreground mb-2">Configure Your Quiz</h2>
                <p className="text-muted-foreground mb-8 text-sm">Select a difficulty level. Our AI will generate unique questions every time.</p>
                
                <div className="grid grid-cols-3 gap-3 mb-8">
                  {['easy', 'medium', 'hard'].map(level => (
                    <button
                      key={level}
                      onClick={() => setDifficulty(level)}
                      className={cn(
                        "py-3 px-4 rounded-xl font-semibold capitalize transition-all border-2",
                        difficulty === level 
                          ? "border-purple-500 bg-purple-500/10 text-purple-600 dark:text-purple-400" 
                          : "border-border/50 hover:border-purple-500/50 text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {level}
                    </button>
                  ))}
                </div>

                <div className="flex justify-center">
                   <button 
                     onClick={handleGenerateQuiz}
                     className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-4 rounded-2xl transition-all shadow-lg active:scale-95 text-lg"
                   >
                     Generate Quiz
                   </button>
                </div>
              </motion.div>
            )}
          </div>
        )}
        
        {isLoading && (
           <div className="h-full flex flex-col justify-center items-center text-center">
             <Loader2 size={48} className="text-purple-500 animate-spin mb-4" />
             <h2 className="text-xl font-bold text-foreground">Analyzing & Generating...</h2>
             <p className="text-muted-foreground mt-2">Crafting challenging questions from the document.</p>
           </div>
        )}

        {questions && !isLoading && (
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} className="max-w-3xl mx-auto w-full space-y-8 pb-32">
            
            {showResults && (
              <div className="bg-card border border-purple-500/30 p-6 rounded-2xl flex items-center justify-between shadow-lg shadow-purple-500/5">
                <div>
                  <h3 className="text-xl font-bold text-foreground mb-1">Quiz Completed!</h3>
                  <p className="text-muted-foreground text-sm">Review your correct and incorrect answers below.</p>
                </div>
                <div className="text-right">
                  <div className="text-4xl font-extrabold text-purple-500">{calculateScore()}%</div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mt-1">Total Score</div>
                </div>
              </div>
            )}

            <div className="space-y-6">
              {questions.map((q, qIndex) => {
                const isAnswered = answers[qIndex] !== undefined;
                const isCorrect = showResults && answers[qIndex] === q.correct_answer;
                const isWrong = showResults && answers[qIndex] !== q.correct_answer;

                return (
                  <div key={qIndex} className="bg-card border border-border p-6 rounded-2xl shadow-sm">
                    <h4 className="font-bold text-lg text-foreground mb-4">
                      <span className="text-purple-500 mr-2">Q{qIndex + 1}.</span> {q.question}
                    </h4>
                    
                    <div className="space-y-3">
                      {q.options.map((opt, oIndex) => {
                        const isSelected = answers[qIndex] === opt;
                        let optionClass = "border-border hover:border-purple-500 border-2 bg-background/50 hover:bg-card text-foreground cursor-pointer";
                        
                        if (isSelected && !showResults) {
                          optionClass = "border-purple-500 bg-purple-500/10 text-purple-600 dark:text-purple-400 font-medium cursor-pointer";
                        }
                        
                        if (showResults) {
                          optionClass = "border-border bg-background/30 text-muted-foreground cursor-default opacity-60"; // default
                          if (opt === q.correct_answer) {
                            optionClass = "border-green-500 bg-green-500/10 text-green-700 dark:text-green-400 font-bold cursor-default opacity-100 ring-2 ring-green-500/20 ring-offset-2 ring-offset-background";
                          } else if (isSelected && isWrong) {
                            optionClass = "border-red-500 bg-red-500/10 text-red-600 dark:text-red-400 font-medium cursor-default opacity-100 ring-2 ring-red-500/20 ring-offset-2 ring-offset-background bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9InJlZCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxsaW5lIHgxPSIxOCIgeTE9IjYiIHgyPSI2IiB5Mj0iMTgiPjwvbGluZT48bGluZSB4MT0iNiIgeTE9IjYiIHgyPSIxOCIgeTI9IjE4Ij48L2xpbmU+PC9zdmc+')] bg-no-repeat bg-[center_right_1rem] bg-[length:1rem_1rem]";
                          }
                        }

                        return (
                          <div 
                            key={oIndex}
                            onClick={() => handleSelectAnswer(qIndex, opt)}
                            className={cn("p-4 rounded-xl transition-all", optionClass)}
                          >
                            {opt}
                          </div>
                        );
                      })}
                    </div>

                    {showResults && (
                      <motion.div initial={{opacity:0, height:0}} animate={{opacity:1, height:'auto'}} className="mt-4 p-4 rounded-xl bg-orange-500/10 border border-orange-500/20 text-orange-800 dark:text-orange-200 text-sm">
                        <span className="font-bold flex items-center gap-1.5 mb-1">
                           <AlertCircle size={16} /> Explanation:
                        </span>
                        {q.explanation}
                      </motion.div>
                    )}
                  </div>
                );
              })}
            </div>
            
            {!showResults ? (
              <div className="flex justify-end mt-8">
                <button 
                  onClick={handleSubmit}
                  className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg active:scale-95"
                >
                  Submit Quiz
                </button>
              </div>
            ) : (
              <div className="mt-12 bg-card p-8 rounded-3xl border border-border shadow-sm flex flex-col items-center">
                 <h4 className="text-xl font-bold mb-6 text-foreground">Want to try again?</h4>
                 <div className="flex items-center gap-4 mb-8 bg-background p-2 rounded-2xl border border-border/50">
                    {['easy', 'medium', 'hard'].map(level => (
                      <button
                        key={`retake-${level}`}
                        onClick={() => setDifficulty(level)}
                        className={cn(
                          "py-2 px-6 rounded-xl font-semibold capitalize transition-all",
                          difficulty === level 
                            ? "bg-purple-500/10 text-purple-600 dark:text-purple-400 shadow-sm border border-purple-500/20" 
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {level}
                      </button>
                    ))}
                 </div>
                 <button 
                   onClick={handleGenerateQuiz}
                   className="bg-foreground hover:bg-foreground/90 text-background font-bold py-3 px-8 rounded-xl transition-all shadow-lg active:scale-95 flex items-center gap-2"
                 >
                   <BrainCircuit size={18} />
                   Generate New Unique Questions
                 </button>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
