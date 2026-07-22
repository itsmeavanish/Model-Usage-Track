import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';

interface AppRow {
  name: string;
  tokens: number;
  requests: number;
}

export const ToolBreakdown = () => {
  const { data, loading } = useLiveData<AppRow[]>('/analytics/by-application');
  const chartData = (data ?? []).map((d) => ({ name: d.name, tokens: d.tokens }));

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Tool / Application Breakdown</h3>
      {loading ? (
        <p className="text-slate-500 animate-pulse">Loading...</p>
      ) : chartData.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
            <XAxis type="number" stroke="#94a3b8" />
            <YAxis dataKey="name" type="category" stroke="#94a3b8" width={90} />
            <Tooltip cursor={{ fill: '#334155' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
            <Legend />
            <Bar dataKey="tokens" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
