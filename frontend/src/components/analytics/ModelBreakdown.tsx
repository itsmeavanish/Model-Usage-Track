import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';
import { formatTokens, formatTokensFull } from '../../utils/format';

interface ModelRow {
  name: string;
  tokens: number;
  requests: number;
}

const COLORS = ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#14b8a6'];

export const ModelBreakdown = () => {
  const { data, loading } = useLiveData<ModelRow[]>('/analytics/by-model');
  const rows = data ?? [];
  const totalTokens = rows.reduce((sum, d) => sum + d.tokens, 0);
  const chartData = rows.map((d) => ({ name: d.name, value: d.tokens }));

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Model Breakdown</h3>
      {loading ? (
        <p className="text-slate-500 animate-pulse">Loading...</p>
      ) : rows.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <div className="flex gap-4 h-[calc(100%-2.5rem)]">
          <div className="h-full w-1/2 min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chartData} cx="50%" cy="50%" labelLine={false} outerRadius={80} fill="#8884d8" dataKey="value">
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="w-1/2 space-y-1.5 overflow-y-auto pr-1 text-sm">
            {rows.map((d, i) => {
              const share = totalTokens > 0 ? (d.tokens / totalTokens) * 100 : 0;
              return (
                <li key={d.name} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 min-w-0">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: COLORS[i % COLORS.length] }}
                    />
                    <span className="truncate text-slate-300" title={d.name}>{d.name}</span>
                  </span>
                  <span className="shrink-0 text-slate-400">
                    <span className="text-slate-200 font-medium" title={`${formatTokensFull(d.tokens)} tokens · ${d.requests} rows`}>
                      {formatTokens(d.tokens)}
                    </span>
                    <span className="ml-2 text-xs">{share.toFixed(1)}%</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};
