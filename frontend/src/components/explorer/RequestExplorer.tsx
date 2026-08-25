import { useContext, useEffect, useState } from 'react';
import { Search, Download, Filter, RefreshCw } from 'lucide-react';
import { apiFetch, API_BASE } from '../../api';
import { LiveRefreshContext } from '../../context/LiveRefresh';
import { formatTokens, formatTokensFull } from '../../utils/format';

interface RequestRow {
  id: number;
  request_id: string;
  source: string;
  provider: string | null;
  timestamp: string;
  model: string;
  total_tokens: number;
  application: string | null;
  user_id: string | null;
  is_reconciled: boolean;
}

const PROVIDERS = [
  { value: '', label: 'All providers' },
  { value: 'zai', label: 'Z.ai (GLM)' },
  { value: 'openai', label: 'OpenAI (GPT)' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
];

const providerLabel = (p: string | null): string =>
  p === 'openai' ? 'OpenAI' : p === 'anthropic' ? 'Anthropic' : p === 'zai' ? 'GLM' : (p ?? '-');

const providerColor = (p: string | null): string =>
  p === 'openai'
    ? 'bg-sky-950/60 border-sky-800/60 text-sky-400'
    : p === 'anthropic'
      ? 'bg-amber-950/60 border-amber-800/60 text-amber-400'
      : 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400';

export const RequestExplorer = () => {
  const { signal } = useContext(LiveRefreshContext);
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [provider, setProvider] = useState('');

  const load = async () => {
    try {
      const path = provider
        ? `/requests/?limit=50&provider=${encodeURIComponent(provider)}`
        : '/requests/?limit=50';
      const data = await apiFetch<RequestRow[]>(path);
      setRequests(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [signal, provider]);

  // Periodic fallback (every 30s) so the table stays fresh even if WS drops.
  useEffect(() => {
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const handleExport = (format: 'csv' | 'json') => {
    window.location.href = `${API_BASE}/requests/export?format=${format}`;
  };

  const visible = filter
    ? requests.filter((r) =>
        [r.request_id, r.model, r.application, r.user_id].some((v) =>
          String(v ?? '').toLowerCase().includes(filter.toLowerCase())
        )
      )
    : requests;

  return (
    <div className="glass-panel p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-white">Request Explorer</h3>
        <div className="flex space-x-3">
          <button
            onClick={load}
            className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sm rounded border border-slate-700 transition-colors"
          >
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
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
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search by ID, model, application, user..."
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="flex items-center px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors text-sm focus:outline-none focus:border-emerald-500"
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
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
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Tokens</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Application</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="text-center py-8 text-slate-500 animate-pulse">Loading requests...</td></tr>
            ) : visible.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-slate-500">No requests found.</td></tr>
            ) : (
              visible.map((req) => (
                <tr key={req.id ?? req.request_id} className="border-b border-slate-800 hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-slate-300">{req.timestamp ? new Date(req.timestamp).toLocaleString() : '-'}</td>
                  <td className="px-4 py-3 text-emerald-400 font-medium">{req.model}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded border text-xs ${providerColor(req.provider)}`}>
                      {providerLabel(req.provider)}
                    </span>
                  </td>
                  <td className="px-4 py-3" title={`${formatTokensFull(req.total_tokens)} tokens`}>{formatTokens(req.total_tokens)}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs">
                      {req.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{req.application || '-'}</td>
                  <td className="px-4 py-3 text-slate-400">{req.user_id || '-'}</td>
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
