import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { useLiveData } from '../../hooks/useLiveData';

interface ProviderRow {
  name: string;
  tokens: number;
  requests: number;
}

// Stable colors per provider so GLM / OpenAI / Anthropic are visually distinct.
const PROVIDER_COLORS: Record<string, string> = {
  zai: '#10b981',
  openai: '#0ea5e9',
  anthropic: '#f59e0b',
};
const FALLBACK = '#8b5cf6';

const labelFor = (name: string): string => {
  switch (name) {
    case 'zai': return 'Z.ai (GLM)';
    case 'openai': return 'OpenAI (GPT)';
    case 'anthropic': return 'Anthropic (Claude)';
    default: return name;
  }
};

export const ProviderBreakdown = () => {
  const { data, loading } = useLiveData<ProviderRow[]>('/analytics/by-provider');
  const chartData = (data ?? []).map((d) => ({
    name: labelFor(d.name),
    key: d.name,
    tokens: d.tokens,
    requests: d.requests,
  }));

  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Usage by Provider</h3>
      {loading ? (
        <p className="text-slate-500 animate-pulse">Loading...</p>
      ) : chartData.length === 0 ? (
        <p className="text-slate-500">No usage recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
            <XAxis type="number" stroke="#94a3b8" />
            <YAxis dataKey="name" type="category" stroke="#94a3b8" width={120} />
            <Tooltip cursor={{ fill: '#334155' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
            <Legend />
            <Bar dataKey="tokens" radius={[0, 4, 4, 0]}>
              {chartData.map((entry) => (
                <Cell key={`cell-${entry.key}`} fill={PROVIDER_COLORS[entry.key] ?? FALLBACK} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
