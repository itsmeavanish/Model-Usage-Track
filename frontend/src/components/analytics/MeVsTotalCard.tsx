import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';
import { formatTokens, formatTokensFull } from '../../utils/format';

interface MeVsTotal {
  identity: string | null;
  mine: { requests: number; tokens: number };
  total: { requests: number; tokens: number };
  trends: { date: string; mine: number; total: number }[];
}

export const MeVsTotalCard = () => {
  const { data, loading } = useLiveData<MeVsTotal>('/analytics/me-vs-total');

  const chartData = (data?.trends ?? []).map((p) => ({
    name: p.date?.slice(5),
    mine: p.mine,
    total: p.total,
  }));

  const myTokens = data?.mine.tokens ?? 0;
  const totalTokens = data?.total.tokens ?? 0;
  const myShare = totalTokens > 0 ? (myTokens / totalTokens) * 100 : 0;

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">My Usage vs Total</h3>
        {data?.identity ? (
          <span className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
            identity: <span className="text-emerald-400">{data.identity}</span>
          </span>
        ) : loading ? (
          <span className="text-xs text-slate-500">loading…</span>
        ) : (
          <span className="text-xs px-2 py-1 rounded bg-rose-950/60 border border-rose-800/60 text-rose-300">
            GLM_MONITOR_USER_IDENTITY not set
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
        <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
          <div className="text-slate-400 text-xs uppercase tracking-wider">Mine</div>
          <div className="text-emerald-400 font-bold" title={`${formatTokensFull(myTokens)} tokens`}>{formatTokens(myTokens)}</div>
        </div>
        <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
          <div className="text-slate-400 text-xs uppercase tracking-wider">Total</div>
          <div className="text-cyan-400 font-bold" title={`${formatTokensFull(totalTokens)} tokens`}>{formatTokens(totalTokens)}</div>
        </div>
        <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
          <div className="text-slate-400 text-xs uppercase tracking-wider">My share</div>
          <div className="text-white font-bold">{myShare.toFixed(1)}%</div>
        </div>
      </div>

      {chartData.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height="60%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" tickFormatter={formatTokens} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
            <Legend />
            <Bar dataKey="total" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            <Line type="monotone" dataKey="mine" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
