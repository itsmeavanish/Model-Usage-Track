import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';

interface ModelRow {
  name: string;
  tokens: number;
  requests: number;
}

const COLORS = ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#14b8a6'];

export const ModelBreakdown = () => {
  const { data, loading } = useLiveData<ModelRow[]>('/analytics/by-model');
  const chartData = (data ?? []).map((d) => ({ name: d.name, value: d.tokens }));

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Model Breakdown</h3>
      {loading ? (
        <p className="text-slate-500 animate-pulse">Loading...</p>
      ) : chartData.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={chartData} cx="50%" cy="50%" labelLine={false} outerRadius={80} fill="#8884d8" dataKey="value">
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
