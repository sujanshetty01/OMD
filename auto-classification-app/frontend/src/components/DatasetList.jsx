import React, { useState, useEffect } from 'react';
import { getDatasets, uploadDataset, triggerSync, syncFromOM } from '../api/client';
import { Upload, FileSpreadsheet, ChevronRight, Database, Clock, Table, CheckCircle2, RefreshCw, Cloud } from 'lucide-react';
import { IngestionProgress } from './IngestionProgress';
import { S3BatchModal } from './S3BatchModal';
import { ingestAllFromS3 } from '../api/client';
import { v4 as uuidv4 } from 'uuid';

export const DatasetList = ({ onSelect }) => {
  const [datasets, setDatasets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [showS3BatchModal, setShowS3BatchModal] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const [fileToUpload, setFileToUpload] = useState(null);
  
  // New state for Batch task
  const [batchTask, setBatchTask] = useState(null);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    const data = await getDatasets();
    setDatasets(data);
  };

  const handleSync = async () => {
      setSyncing(true);
      try {
          await triggerSync();
          await loadDatasets();
      } catch(e) {
          console.error(e);
      } finally {
          setSyncing(false);
      }
  };

  const handleUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const newSessionId = uuidv4();
    setSessionId(newSessionId);
    setFileToUpload(file);
    setS3Task(null); // Clear S3 task
    setUploading(true);
    setShowProgress(true);
  };

  const handleBatchIngest = (bucket) => {
    const newSessionId = uuidv4();
    setSessionId(newSessionId);
    setBatchTask({ bucket });
    setUploading(true);
    setShowProgress(true);
  };

  const startIngestionProcess = async () => {
    try {
      if (batchTask) {
        // Batch S3
        await ingestAllFromS3(batchTask.bucket, sessionId);
      } else if (fileToUpload) {
        // File Path
        await uploadDataset(fileToUpload, sessionId);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const onIngestionComplete = () => {
    setUploading(false);
    setShowProgress(false);
    setBatchTask(null);
    setFileToUpload(null);
    loadDatasets();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white/50 backdrop-blur-sm p-4 rounded-xl border border-white/40 shadow-sm">
        <h2 className="text-lg font-bold flex items-center gap-2 text-slate-800">
          <div className="p-1.5 bg-indigo-100 text-indigo-700 rounded-lg">
             <Database size={18} />
          </div>
          Your Datasets
          <span className="text-xs font-normal text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{datasets.length} Total</span>
        </h2>
        
        <div className="flex items-center gap-2">
            <button 
                onClick={handleSync}
                disabled={syncing}
                className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-white rounded-lg transition-all disabled:opacity-50"
                title="Sync from External Sources"
            >
                <RefreshCw size={18} className={syncing ? "animate-spin" : ""} />
            </button>
            <div className="h-6 w-px bg-slate-200 mx-1"></div>
            
            <button 
                onClick={() => setShowS3BatchModal(true)}
                className="btn-secondary flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-white hover:text-indigo-600 transition-all border border-transparent hover:border-slate-200"
            >
                <Cloud size={18} /> Ingest from S3
            </button>

            <div className="relative group">
              <input
                type="file"
                onChange={handleUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                accept=".csv,.json,.xlsx,.xls,.parquet,.xml,.pdf,.yaml,.yml"
                disabled={uploading}
              />
              <button className="btn-primary">
                <Upload size={18} />
                {uploading ? 'Processing...' : 'Upload New Dataset'}
              </button>
            </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {datasets.length === 0 && (
          <div className="col-span-full p-12 text-center text-slate-500 bg-white/40 rounded-2xl border border-dashed border-slate-300">
            <div className="mx-auto bg-slate-100 w-16 h-16 rounded-full flex items-center justify-center mb-4">
              <Database size={32} className="text-slate-400" />
            </div>
            <p className="text-lg font-medium text-slate-700">No datasets found</p>
            <p className="text-sm mt-1">Upload a CSV or JSON file to get started.</p>
          </div>
        )}
        {datasets.map((d) => (
          <div 
            key={d.id} 
            onClick={() => onSelect(d.id)}
            className="glass-card p-6 rounded-2xl relative group cursor-pointer flex flex-col gap-4"
          >
            <div className="flex justify-between items-start">
               <div className="p-3 bg-gradient-to-br from-blue-50 to-indigo-50 text-blue-600 rounded-xl border border-blue-100 group-hover:scale-105 transition-transform duration-300">
                  <FileSpreadsheet size={24} />
               </div>
               <div className="px-2 py-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase tracking-wide rounded-full border border-emerald-100 flex items-center gap-1">
                  <CheckCircle2 size={10} /> Synced
               </div>
            </div>

            <div>
              <h3 className="font-bold text-lg text-slate-900 group-hover:text-blue-700 transition-colors line-clamp-1">{d.name}</h3>
              <div className="flex items-center gap-3 text-sm text-slate-500 mt-2">
                 <span className="flex items-center gap-1 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                    <Table size={14} /> {d.row_count} rows
                 </span>
                 <span className="flex items-center gap-1">
                    <Clock size={14} /> {new Date(d.created_at).toLocaleDateString()}
                 </span>
              </div>
            </div>

            <div className="mt-auto pt-4 border-t border-slate-100 flex justify-between items-center text-xs font-medium text-indigo-600 opacity-0 group-hover:opacity-100 transition-all transform translate-y-1 group-hover:translate-y-0">
               <span>View Analysis</span>
               <ChevronRight size={16} />
            </div>
          </div>
        ))}
      </div>
      
      {showProgress && (
        <IngestionProgress 
          clientId={sessionId} 
          onComplete={onIngestionComplete}
          onClose={() => setShowProgress(false)}
          onReady={startIngestionProcess}
        />
      )}

      {showS3BatchModal && (
        <S3BatchModal 
          onClose={() => setShowS3BatchModal(false)}
          onIngest={handleBatchIngest}
        />
      )}
    </div>
  );
};
