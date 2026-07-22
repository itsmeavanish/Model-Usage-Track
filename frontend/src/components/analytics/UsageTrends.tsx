import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';

interface TrendsPoint {
  date: string;
  tokens: number;
  requests: number;
}

export const UsageTrends = () => {
  const { data, loading } = useLiveData<TrendsPoint[]>('/analytics/trends?days=7');

  const chartData = (data ?? []).map((p) => ({
    name: p.date?.slice(5),
    usage: p.tokens,
    requests: p.requests,
  }));

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Usage Trends (7 days)</h3>
      {loading ? (
        <p className="text-slate-500 animate-pulse">Loading...</p>
      ) : chartData.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              itemStyle={{ color: '#10b981' }}
            />
            <Legend />
            <Line type="monotone" dataKey="usage" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 8 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
