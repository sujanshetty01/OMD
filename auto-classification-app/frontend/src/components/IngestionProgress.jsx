import React, { useEffect, useState } from 'react';
import { CheckCircle2, Circle, Loader2, AlertCircle, Sparkles } from 'lucide-react';

export const IngestionProgress = ({ clientId, onComplete, onClose, onReady }) => {
  const [steps, setSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState("");
  const [status, setStatus] = useState("processing");

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/ingestion/${clientId}`);
    
    ws.onopen = () => {
      console.log("WebSocket Connected");
      if (onReady) onReady();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setCurrentStep(data.step);
      
      if (data.status === "complete") {
        setStatus("complete");
        setSteps(prev => [...prev, { text: data.step, status: 'complete' }]);
        setTimeout(() => onComplete(), 1500);
      } else if (data.status === "error") {
        setStatus("error");
        setSteps(prev => [...prev, { text: data.step, status: 'error' }]);
      } else {
        setSteps(prev => {
           if (prev.find(s => s.text === data.step)) return prev;
           return [...prev, { text: data.step, status: 'complete' }];
        });
      }
    };

    return () => {
      if (ws.readyState === 1 || ws.readyState === 0) {
        ws.close();
      }
    };
  }, [clientId]);

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all animate-in fade-in zoom-in duration-300">
        <div className="p-6 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Sparkles size={20} className="animate-pulse" />
            </div>
            <div>
              <h3 className="font-bold text-lg">AI Ingestion Flow</h3>
              <p className="text-xs text-slate-400">Executing multi-layer storage strategy</p>
            </div>
          </div>
          {status === "error" && (
            <button onClick={onClose} className="text-slate-400 hover:text-white transition">
              <AlertCircle size={20} />
            </button>
          )}
        </div>

        <div className="p-8 space-y-6">
          <div className="space-y-4">
            {steps.map((step, i) => (
              <div key={i} className="flex items-center gap-3 text-sm animate-in slide-in-from-left duration-300">
                <CheckCircle2 size={18} className="text-green-500 shrink-0" />
                <span className="text-slate-600">{step.text}</span>
              </div>
            ))}
            
            {status === "processing" && currentStep && !steps.find(s => s.text === currentStep) && (
              <div className="flex items-center gap-3 text-sm font-medium text-blue-600">
                <Loader2 size={18} className="animate-spin shrink-0" />
                <span>{currentStep}</span>
              </div>
            )}
          </div>

          {status === "complete" && (
            <div className="p-4 bg-green-50 border border-green-100 rounded-xl flex items-center gap-3 text-green-800 animate-in fade-in duration-500">
              <CheckCircle2 size={24} className="text-green-600" />
              <div>
                <p className="font-bold">Ingestion Successful</p>
                <p className="text-xs">All layers synced and indexed.</p>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="p-4 bg-red-50 border border-red-100 rounded-xl flex items-center gap-3 text-red-800">
              <AlertCircle size={24} className="text-red-600" />
              <div>
                <p className="font-bold">Ingestion Halted</p>
                <p className="text-xs">Check server logs for details.</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="px-8 pb-8">
           <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-500 ${status === 'complete' ? 'w-full bg-green-500' : 'w-2/3 bg-blue-600 animate-pulse'}`}
              ></div>
           </div>
        </div>
      </div>
    </div>
  );
};
