import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Bot, Sparkles, Database, ShieldCheck, User, Zap } from 'lucide-react';

const API_URL = "http://localhost:8000/api/ai";

const SUGGESTIONS = [
  "Show me all datasets containing PII",
  "How many email addresses did we find?",
  "List all columns with sensitive data",
  "What is the row count for the latest upload?"
];

export const AIAssistant = () => {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [chat, setChat] = useState([]);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chat]);

  const handleQuery = async (e, overridePrompt = null) => {
    if (e) e.preventDefault();
    const text = overridePrompt || prompt;
    if (!text.trim()) return;

    const userMsg = { role: 'user', content: text };
    setChat(prev => [...prev, userMsg]);
    setPrompt("");
    setLoading(true);

    try {
      const resp = await axios.post(`${API_URL}/query`, { prompt: text });
      const aiMsg = { 
        role: 'assistant', 
        content: resp.data.answer,
        classifications: resp.data.classifications 
      };
      setChat(prev => [...prev, aiMsg]);
    } catch (err) {
      setChat(prev => [...prev, { role: 'assistant', content: "Sorry, I had trouble connecting to the AI Engine Layers." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-220px)] glass-panel rounded-2xl overflow-hidden shadow-xl border-0 ring-1 ring-black/5">
      {/* Header */}
      <div className="p-5 bg-slate-900 text-white flex items-center justify-between relative overflow-hidden">
        {/* Abstract BG */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500 rounded-full mix-blend-overlay filter blur-3xl opacity-20 translate-x-1/2 -translate-y-1/2"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-violet-500 rounded-full mix-blend-overlay filter blur-3xl opacity-20 -translate-x-1/2 translate-y-1/2"></div>

        <div className="flex items-center gap-4 relative z-10">
          <div className="p-3 bg-gradient-to-br from-blue-600 to-violet-600 rounded-xl shadow-lg ring-1 ring-white/20">
            <Bot size={24} className="text-white" />
          </div>
          <div>
            <h2 className="font-bold text-lg flex items-center gap-2">
              Promptiq AI Engine
              <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-200 text-[10px] uppercase font-bold tracking-wider border border-blue-500/30">Beta</span>
            </h2>
            <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
               <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
               Connected to VectorDB • MinIO • OpenMetadata
            </p>
          </div>
        </div>
        <Sparkles size={20} className="text-yellow-400 animate-pulse relative z-10" />
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
        {chat.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 text-center px-8 animate-in fade-in zoom-in-95 duration-500">
            <div className="w-20 h-20 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-6">
               <Database size={40} className="text-indigo-200" />
            </div>
            <p className="text-xl font-bold text-slate-700">Internal Data Brain</p>
            <p className="text-sm max-w-md mt-2 mb-8">Ask natural language questions about your uploaded datasets. I will search through the semantic AI layers to find specific answers.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-xl">
               {SUGGESTIONS.map((s, i) => (
                 <button 
                    key={i}
                    onClick={(e) => handleQuery(e, s)}
                    className="p-3 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 hover:border-blue-400 hover:text-blue-600 hover:shadow-md transition-all text-left flex items-center gap-2"
                 >
                    <Zap size={14} className="text-yellow-500" /> {s}
                 </button>
               ))}
            </div>
          </div>
        )}
        
        {chat.map((msg, i) => (
          <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-300`}>
            {msg.role === 'assistant' && (
               <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white shadow-sm mt-1 shrink-0">
                  <Bot size={16} />
               </div>
            )}
            
            <div className={`max-w-[80%] p-4 rounded-2xl shadow-sm ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-sm' 
                : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm'
            }`}>
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
              {msg.classifications && msg.classifications.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100/50 flex flex-wrap gap-2 text-xs">
                  <span className="text-slate-400 font-medium">References:</span>
                  {msg.classifications.map(tag => (
                    <span key={tag} className="px-2 py-0.5 bg-green-50 text-green-700 border border-green-200/50 rounded-full flex items-center gap-1 font-medium">
                      <ShieldCheck size={10} /> {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
               <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 mt-1 shrink-0">
                  <User size={16} />
               </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-4">
             <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white shadow-sm mt-1">
                  <Bot size={16} />
             </div>
             <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-bl-sm shadow-sm flex gap-2 w-fit items-center">
                <span className="text-xs text-slate-400 font-medium mr-2">Thinking</span>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-.15s]"></div>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-.3s]"></div>
             </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleQuery} className="p-4 bg-white border-t border-slate-100 flex gap-3 relative z-20">
        <input 
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask something about the data..."
          className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400"
        />
        <button 
          disabled={loading || !prompt.trim()}
          className="p-3 bg-blue-600 text-white rounded-xl hover:shadow-lg hover:shadow-blue-500/20 active:scale-95 disabled:opacity-50 disabled:scale-100 transition-all"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};
