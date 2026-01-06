import React, { useState } from 'react';
import { DatasetList } from './components/DatasetList';
import { DatasetDetail } from './components/DatasetDetail';
import { AIAssistant } from './components/AIAssistant';
import { ScanSearch, LayoutGrid, MessageSquare, ShieldCheck, Activity } from 'lucide-react';

function App() {
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [activeTab, setActiveTab] = useState('catalog');

  return (
    <div className="min-h-screen text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Glass Header */}
      <header className="sticky top-0 z-50 glass-panel border-b-0 border-white/20 shadow-sm mb-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-violet-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-500/20">
              <ScanSearch size={26} strokeWidth={2.5} />
            </div>
            <div>
              <span className="font-bold text-2xl bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700 tracking-tight">AutoClassify</span>
              <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full w-fit mt-0.5 border border-emerald-100">
                <Activity size={10} /> System Online
              </div>
            </div>
          </div>
          
          <div className="flex p-1.5 glass-panel rounded-xl gap-1">
            <button 
              onClick={() => { setActiveTab('catalog'); setSelectedDatasetId(null); }}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === 'catalog' 
                  ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-black/5' 
                  : 'text-slate-500 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <LayoutGrid size={18} /> Catalog
            </button>
            <button 
              onClick={() => setActiveTab('ai')}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                activeTab === 'ai' 
                  ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-black/5' 
                  : 'text-slate-500 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <MessageSquare size={18} /> AI Assistant
            </button>
          </div>

          <div className="text-right hidden sm:block">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Enterprise Edition</div>
            <div className="flex items-center justify-end gap-1 text-xs text-indigo-600 font-medium">
               <ShieldCheck size={12} /> Secure Environment
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        {activeTab === 'catalog' ? (
          selectedDatasetId ? (
            <DatasetDetail 
              datasetId={selectedDatasetId} 
              onBack={() => setSelectedDatasetId(null)} 
            />
          ) : (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-col gap-2 relative">
                <h1 className="text-4xl font-bold text-slate-900 tracking-tight">Data Catalog</h1>
                <p className="text-lg text-slate-600 max-w-2xl">
                  Upload datasets to automatically detect PII, classify sensitivity, and sync with your governance platform.
                </p>
              </div>
              <DatasetList onSelect={setSelectedDatasetId} />
            </div>
          )
        ) : (
          <div className="max-w-5xl mx-auto animate-in fade-in zoom-in-95 duration-500">
             <div className="mb-8 text-center space-y-2">
              <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 pb-1">AI Data Assistant</h1>
              <p className="text-slate-600 text-lg">Semantically search across your vector database and metadata store.</p>
            </div>
            <AIAssistant />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
