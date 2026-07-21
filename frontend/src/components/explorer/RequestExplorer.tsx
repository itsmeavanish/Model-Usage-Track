import React, { useState, useEffect } from 'react';
import { Search, Download, Filter } from 'lucide-react';

export const RequestExplorer = () => {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/requests/?limit=20')
      .then(res => res.json())
      .then(data => {
        setRequests(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleExport = (format: 'csv' | 'json') => {
    window.location.href = `http://localhost:8000/api/v1/requests/export?format=${format}`;
  };

  return (
    <div className="glass-panel p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-white">Request Explorer</h3>
        <div className="flex space-x-3">
          <button onClick={() => handleExport('csv')} className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sm rounded border border-slate-700 transition-colors">
            <Download size={14} />
            <span>CSV</span>
          </button>
          <button onClick={() => handleExport('json')} className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sm rounded border border-slate-700 transition-colors">
            <Download size={14} />
            <span>JSON</span>
          </button>
        </div>
      </div>

      <div className="flex space-x-4 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search by ID or metadata..." 
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>
        <button className="flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors">
          <Filter size={16} />
          <span>Filters</span>
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-700">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Tokens</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Application</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-8 text-slate-500 animate-pulse">Loading requests...</td></tr>
            ) : requests.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-8 text-slate-500">No requests found.</td></tr>
            ) : (
              requests.map((req, i) => (
                <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-slate-300">{new Date(req.timestamp).toLocaleString()}</td>
                  <td className="px-4 py-3 text-emerald-400 font-medium">{req.model}</td>
                  <td className="px-4 py-3">{req.total_tokens.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs">
                      {req.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{req.application || '-'}</td>
                  <td className="px-4 py-3">
                    {req.is_reconciled ? (
                      <span className="text-emerald-500 text-xs font-medium">Reconciled</span>
                    ) : (
                      <span className="text-amber-500 text-xs font-medium">Raw</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
