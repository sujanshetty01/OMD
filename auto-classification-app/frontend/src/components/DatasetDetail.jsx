import React, { useState, useEffect } from 'react';
import { getDataset, getColumns, applyTag } from '../api/client';
import { TagBadge } from './TagBadge';
import { ArrowLeft, Table, Box, FileText, BarChart3, ShieldAlert, CheckCircle, Plus, X, Check } from 'lucide-react';

export const DatasetDetail = ({ datasetId, onBack }) => {
  const [dataset, setDataset] = useState(null);
  const [columns, setColumns] = useState([]);
  const [stats, setStats] = useState({ piiCount: 0, classifiedCount: 0 });
  const [activeCol, setActiveCol] = useState(null);
  const [tagInput, setTagInput] = useState("");

  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [datasetId]);

  const loadData = async () => {
      try {
          const d = await getDataset(datasetId);
          setDataset(d);
          const c = await getColumns(datasetId);
          setColumns(c);

          // Calc stats
          let pii = 0;
          let classified = 0;
          c.forEach(col => {
            if (col.tags.length > 0) classified++;
            if (col.tags.some(t => t.tag_fqn.includes('PII') || t.tag_fqn.includes('Sensitive'))) pii++;
          });
          setStats({ piiCount: pii, classifiedCount: classified });
      } catch (err) {
          console.error("Failed to load dataset", err);
          setError("Failed to load dataset details. It may have been deleted or corrupted.");
      }
  };

  const handleAddTag = async (columnName) => {
    if (!tagInput) return;
    try {
        await applyTag(datasetId, columnName, tagInput);
        await loadData(); // Reload to show new tag
        setActiveCol(null);
        setTagInput("");
    } catch (e) {
        console.error("Failed to add tag", e);
    }
  };

  if (error) return (
    <div className="flex flex-col items-center justify-center p-12 text-slate-500 gap-4 animate-in fade-in zoom-in-95">
        <div className="bg-red-50 text-red-600 p-4 rounded-full"><ShieldAlert size={32}/></div>
        <h3 className="text-lg font-bold text-slate-800">Error Loading Dataset</h3>
        <p className="text-center max-w-md">{error}</p>
        <button onClick={onBack} className="mt-4 px-4 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors shadow-sm font-medium">
            Back to Catalog
        </button>
    </div>
  );

  if (!dataset) return (
    <div className="flex flex-col items-center justify-center p-12 text-slate-500 gap-4">
      <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
      <p>Loading analysis...</p>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Header & Stats */}
      <div className="space-y-6">
        <button 
          onClick={onBack} 
          className="group flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-600 transition-colors"
        >
          <div className="p-1 rounded-full bg-slate-100 group-hover:bg-indigo-100 transition-colors">
            <ArrowLeft size={16} /> 
          </div>
          Back to Catalog
        </button>

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">{dataset.name}</h1>
            <p className="text-slate-500 mt-1 flex items-center gap-2">
               <FileText size={16} /> Dataset Analysis Report
            </p>
          </div>
          <div className="flex gap-2">
             <span className="badge badge-blue">
                <CheckCircle size={12} className="mr-1" /> Active
             </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass-panel p-5 rounded-xl flex items-center gap-4">
             <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                <Table size={24} />
             </div>
             <div>
                <p className="text-sm font-medium text-slate-500">Total Rows</p>
                <p className="text-2xl font-bold text-slate-900">{dataset.row_count.toLocaleString()}</p>
             </div>
          </div>
          <div className="glass-panel p-5 rounded-xl flex items-center gap-4">
             <div className="p-3 bg-violet-50 text-violet-600 rounded-lg">
                <Box size={24} />
             </div>
             <div>
                <p className="text-sm font-medium text-slate-500">Columns Analyzed</p>
                <div className="flex items-baseline gap-2">
                   <p className="text-2xl font-bold text-slate-900">{columns.length}</p>
                   <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-1.5 py-0.5 rounded-full">100% Scanned</span>
                </div>
             </div>
          </div>
          <div className="glass-panel p-5 rounded-xl flex items-center gap-4 border-l-4 border-l-orange-400">
             <div className="p-3 bg-orange-50 text-orange-600 rounded-lg">
                <ShieldAlert size={24} />
             </div>
             <div>
                <p className="text-sm font-medium text-slate-500">Sensitive Columns</p>
                <p className="text-2xl font-bold text-slate-900">{stats.piiCount}</p>
             </div>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="glass-panel rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white/50">
           <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
              <BarChart3 size={20} className="text-indigo-600" />
              Column Classification
           </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50/80 border-b border-slate-200 backdrop-blur-sm">
              <tr>
                <th className="px-6 py-4 font-semibold text-slate-900">Column Name</th>
                <th className="px-6 py-4 font-semibold text-slate-900">Type</th>
                <th className="px-6 py-4 font-semibold text-slate-900">AI Classification</th>
                <th className="px-6 py-4 font-semibold text-slate-900 w-1/3">Data Sample</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white/40">
              {columns.map((col) => {
                const samples = JSON.parse(col.sample_values || "[]");
                const isSensitive = col.tags.some(t => t.tag_fqn.includes('PII'));
                return (
                  <tr key={col.name} className={`hover:bg-indigo-50/30 transition-colors ${isSensitive ? 'bg-orange-50/10' : ''}`}>
                    <td className="px-6 py-4 font-medium text-slate-900">
                       <div className="flex items-center gap-2">
                          {isSensitive && <ShieldAlert size={14} className="text-orange-500" />}
                          {col.name}
                       </div>
                    </td>
                    <td className="px-6 py-4">
                       <span className="font-mono text-[10px] bg-slate-100 px-2 py-1 rounded text-slate-600 uppercase border border-slate-200">
                          {col.datatype}
                       </span>
                    </td>
                    <td className="px-6 py-4">
                      
                      <div className="flex flex-wrap gap-2 items-center relative">
                        {col.tags.length === 0 && <span className="text-slate-400 text-xs flex items-center gap-1 italic">No tags</span>}
                        {col.tags.map((tag) => (
                          <TagBadge 
                            key={tag.tag_fqn} 
                            tag={tag.tag_fqn}
                            confidence={tag.confidence}
                            source={tag.source}
                            is_auto={tag.is_auto_applied}
                          />
                        ))}
                        
                        <button 
                            onClick={() => { setActiveCol(col.name); setTagInput(""); }} 
                            className="p-1 rounded-full hover:bg-slate-200 text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Add manual classification"
                        >
                            <Plus size={14} />
                        </button>

                        {activeCol === col.name && (
                            <div className="absolute left-0 top-full mt-2 bg-white shadow-xl border border-slate-200 p-2 rounded-lg z-20 flex gap-1 items-center animate-in zoom-in-95 duration-200 min-w-[200px]">
                                <select 
                                    className="text-xs border-slate-300 rounded-md py-1 pl-1 pr-6 flex-1 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    value={tagInput}
                                    onChange={(e) => setTagInput(e.target.value)}
                                    autoFocus
                                >
                                    <option value="">Select Tag...</option>
                                    <option value="PII.Sensitive">PII.Sensitive</option>
                                    <option value="PII.NonSensitive">PII.NonSensitive</option>
                                    <option value="PersonalData.Personal">PersonalData.Personal</option>
                                    <option value="PersonalData.SpecialCategory">PersonalData.SpecialCategory</option>
                                </select>
                                <button onClick={() => handleAddTag(col.name)} disabled={!tagInput} className="p-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"><Check size={14}/></button>
                                <button onClick={() => setActiveCol(null)} className="p-1 text-slate-500 hover:bg-slate-100 rounded"><X size={14}/></button>
                            </div>
                        )}
                      </div>

                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      <div className="flex flex-wrap gap-1.5">
                        {samples.slice(0, 3).map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-white rounded border border-slate-200 truncate max-w-[150px] shadow-sm">
                            {s}
                          </span>
                        ))}
                        {samples.length > 3 && <span className="text-xs text-slate-400 self-center">+{samples.length - 3} more</span>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
