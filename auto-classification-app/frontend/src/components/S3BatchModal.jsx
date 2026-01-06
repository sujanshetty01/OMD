import React, { useState, useEffect } from 'react';
import { listS3Buckets, listS3Objects, ingestAllFromS3 } from '../api/client';
import { X, Server, FileText, Database, ArrowRight, Loader2, PlayCircle, FolderOpen } from 'lucide-react';

export const S3BatchModal = ({ onClose, onIngest }) => {
  const [buckets, setBuckets] = useState([]);
  const [selectedBucket, setSelectedBucket] = useState('');
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewingObjects, setViewingObjects] = useState(false);

  useEffect(() => {
    loadBuckets();
  }, []);

  const loadBuckets = async () => {
    setLoading(true);
    try {
      const data = await listS3Buckets();
      setBuckets(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleBucketSelect = async (bucket) => {
    setSelectedBucket(bucket);
    setLoading(true);
    try {
      const objs = await listS3Objects(bucket);
      setObjects(objs);
      setViewingObjects(true);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleIngestAll = () => {
    if (selectedBucket) {
      onIngest(selectedBucket);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${viewingObjects ? 'bg-indigo-100 text-indigo-600' : 'bg-orange-100 text-orange-600'}`}>
               {viewingObjects ? <FolderOpen size={20} /> : <Server size={20} />}
            </div>
            <div>
              <h3 className="font-bold text-lg text-slate-900">
                {viewingObjects ? `Bucket: ${selectedBucket}` : "Select S3 Bucket"}
              </h3>
              <p className="text-xs text-slate-500">
                {viewingObjects ? "Review content below or start batch job" : "Choose a source for bulk ingestion"}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 bg-slate-50/30">
            {loading ? (
              <div className="flex justify-center py-12 text-slate-400">
                <Loader2 size={32} className="animate-spin" />
              </div>
            ) : !viewingObjects ? (
              // BUCKET LIST
              <div className="grid grid-cols-1 gap-2">
                {buckets.length === 0 ? <div className="text-center text-slate-400 py-8">No buckets found</div> : null}
                {buckets.map(b => (
                  <button
                    key={b}
                    onClick={() => handleBucketSelect(b)}
                    className="w-full text-left px-4 py-3 bg-white hover:bg-white border border-slate-200 hover:border-orange-300 hover:shadow-md rounded-xl transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-3">
                       <div className="p-2 bg-orange-50 text-orange-600 rounded-lg group-hover:scale-110 transition-transform">
                          <Database size={18} />
                       </div>
                       <span className="font-semibold text-slate-700">{b}</span>
                    </div>
                    <ArrowRight size={16} className="text-slate-300 group-hover:text-orange-500 group-hover:translate-x-1 transition-all" />
                  </button>
                ))}
              </div>
            ) : (
              // OBJECT PREVIEW LIST
              <div>
                  <div className="mb-4 flex items-center justify-between">
                     <button onClick={() => setViewingObjects(false)} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1">
                        ← Back to Buckets
                     </button>
                     <span className="text-xs font-medium text-slate-400">{objects.length} Objects Found</span>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden divide-y divide-slate-100">
                      {objects.slice(0, 10).map((obj, i) => (
                          <div key={i} className="px-4 py-2 text-sm text-slate-600 flex items-center gap-2">
                              <FileText size={14} className="text-slate-400" />
                              <span className="truncate">{obj.Key}</span>
                          </div>
                      ))}
                      {objects.length > 10 && (
                          <div className="px-4 py-2 text-xs text-center text-slate-400 bg-slate-50">
                              + {objects.length - 10} more files...
                          </div>
                      )}
                  </div>
              </div>
            )}
        </div>

        {/* Footer */}
        {viewingObjects && (
            <div className="p-4 border-t border-slate-100 bg-white flex justify-end z-10">
                <button 
                onClick={handleIngestAll}
                className="w-full px-4 py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg hover:shadow-xl hover:from-indigo-700 hover:to-violet-700 transition-all flex items-center justify-center gap-2"
                >
                <PlayCircle size={18} /> Process All {objects.length} Files
                </button>
            </div>
        )}
      </div>
    </div>
  );
};
