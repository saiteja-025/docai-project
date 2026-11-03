import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, FileText, Loader2, CheckCircle2, AlertCircle, RotateCcw } from 'lucide-react';
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

  const handleRetakeQuiz = () => {
    setAnswers({});
    setShowResults(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectAnswer = (qIndex, option) => {
    if (showResults) return;
    setAnswers(prev => ({ ...prev, [qIndex]: option }));
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (Object.keys(answers).length < questions.length) {
      alert("Please answer all questions before submitting.");
      return;
    }

    // Persist score directly to sync with Dashboard overview
    const finalScore = calculateScore();
    try {
      const token = localStorage.getItem('docToken');
      await axios.post(`${API_BASE_URL}/quiz/submit`, 
        { score: finalScore, answers_json: JSON.stringify(answers) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setShowResults(true);
      window.scrollTo(0, 0); // Scroll to top to see score
    } catch (e) {
      console.error("Failed to save score to database", e);
      alert("Error submitting quiz results.");
      setShowResults(true); // Still show results even if saving failed
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
                  "w-full text-left p-4 rounded-xl border transition-all text-sm font-medium cursor-pointer",
                  selectedDocId === doc.id
                    ? "bg-purple-600 border-purple-500 text-white shadow-md shadow-purple-500/20"
                    : "bg-background border-border text-foreground hover:border-purple-500/50 hover:bg-card"
                )}
              >
                <div className="line-clamp-2">{doc.title}</div>
                <div className={cn(
                  "text-[10px] mt-1 font-medium uppercase tracking-wider",
                  selectedDocId === doc.id ? "text-purple-200" : "text-muted-foreground"
                )}>
                  Ready for Quiz
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-8 relative z-10">
        {!selectedDocId && (
          <div className="h-full flex flex-col justify-center items-center text-center opacity-70">
            <BrainCircuit size={64} className="text-purple-500/40 mb-4" />
            <h3 className="text-xl font-bold text-foreground">No Document Selected</h3>
            <p className="text-muted-foreground mt-2 max-w-sm">
              Please pick an uploaded document from the left to generate customized multiple-choice tests.
            </p>
          </div>
        )}

        {selectedDocId && !questions && !isLoading && (
          <div className="h-full flex flex-col justify-center items-center max-w-md mx-auto text-center">
            <div className="p-4 bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded-3xl mb-6">
               <FileText size={48} />
            </div>
            
            <h3 className="text-2xl font-extrabold text-foreground mb-2">
              {documents.find(d => d.id === selectedDocId)?.title}
            </h3>
            <p className="text-muted-foreground text-sm mb-8 leading-relaxed">
              Our AI extracts key conceptual hooks, definitions, and facts from this file to craft 5 interactive questions.
            </p>

            {/* Difficulty Selector */}
            <div className="w-full mb-8 bg-card p-4 rounded-2xl border border-border">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-3 text-left">
                Select Difficulty
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['easy', 'medium', 'hard'].map(level => (
                  <button
                    key={level}
                    onClick={() => setDifficulty(level)}
                    className={cn(
                      "py-2.5 rounded-xl font-semibold capitalize text-sm transition-all cursor-pointer",
                      difficulty === level 
                        ? "bg-purple-600 text-white shadow-md shadow-purple-500/20" 
                        : "bg-background border border-border text-foreground hover:bg-muted"
                    )}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>

            <button 
              onClick={handleGenerateQuiz}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-4 rounded-2xl transition-all shadow-lg shadow-purple-500/25 active:scale-95 text-lg cursor-pointer flex items-center justify-center gap-2"
            >
              <BrainCircuit size={20} />
              Generate Quiz
            </button>
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
                          optionClass = "border-border bg-background/30 text-muted-foreground cursor-default opacity-60";
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
                  className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg active:scale-95 z-50 relative pointer-events-auto cursor-pointer"
                >
                  Submit Quiz
                </button>
              </div>
            ) : (
              <div className="mt-12 bg-card p-8 rounded-3xl border border-border shadow-sm flex flex-col items-center">
                 <h4 className="text-xl font-bold mb-6 text-foreground">Next Steps</h4>
                 <div className="flex items-center gap-4 mb-8 bg-background p-2 rounded-2xl border border-border/50">
                    {['easy', 'medium', 'hard'].map(level => (
                      <button
                        key={`retake-${level}`}
                        onClick={() => setDifficulty(level)}
                        className={cn(
                          "py-2 px-6 rounded-xl font-semibold capitalize transition-all cursor-pointer",
                          difficulty === level 
                            ? "bg-purple-500/10 text-purple-600 dark:text-purple-400 shadow-sm border border-purple-500/20" 
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {level}
                      </button>
                    ))}
                 </div>
                 <div className="flex flex-wrap gap-4 justify-center">
                   <button 
                     onClick={handleRetakeQuiz}
                     className="bg-secondary text-secondary-foreground hover:bg-secondary/80 font-bold py-3 px-6 rounded-xl transition-all shadow-sm active:scale-95 flex items-center gap-2 cursor-pointer"
                   >
                     <RotateCcw size={18} />
                     Retake This Quiz
                   </button>
                   <button 
                     onClick={handleGenerateQuiz}
                     className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-6 rounded-xl transition-all shadow-lg active:scale-95 flex items-center gap-2 cursor-pointer"
                   >
                     <BrainCircuit size={18} />
                     Generate New Unique Questions
                   </button>
                 </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
