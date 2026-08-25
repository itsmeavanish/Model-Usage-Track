import { useLiveData } from '../../hooks/useLiveData';
import { formatTokens, formatTokensFull } from '../../utils/format';

interface HeatPoint {
  date: string;
  tokens: number;
  requests: number;
}

function colorFor(tokens: number, max: number): string {
  if (tokens <= 0 || max <= 0) return 'bg-slate-800';
  const ratio = tokens / max;
  if (ratio > 0.75) return 'bg-emerald-400';
  if (ratio > 0.4) return 'bg-emerald-600';
  if (ratio > 0.05) return 'bg-emerald-900';
  return 'bg-slate-800';
}

export const HeatmapCalendar = () => {
  const { data } = useLiveData<HeatPoint[]>('/analytics/heatmap?days=84');
  const points = data ?? [];
  const max = points.reduce((m, p) => Math.max(m, p.tokens), 0);

  return (
    <div className="glass-panel p-6 w-full">
      <h3 className="text-lg font-semibold mb-4">Daily Activity Intensity</h3>
      <div className="flex space-x-1 items-end h-24 overflow-x-auto pb-2">
        {points.length === 0 ? (
          <p className="text-slate-500">No activity yet.</p>
        ) : (
          points.map((d, i) => (
            <div key={i} className="flex flex-col items-center group relative cursor-pointer">
              <div className={`w-4 h-4 rounded-sm ${colorFor(d.tokens, max)}`} />
              <div className="hidden group-hover:block absolute bottom-full mb-2 bg-slate-800 text-xs px-2 py-1 rounded text-nowrap border border-slate-700 z-10">
                {d.date}: {formatTokens(d.tokens)} tokens ({d.requests} requests · {formatTokensFull(d.tokens)})
              </div>
            </div>
          ))
        )}
      </div>
      <div className="flex justify-end items-center space-x-2 mt-4 text-xs text-slate-500">
        <span>Less</span>
        <div className="flex space-x-1">
          <div className="w-3 h-3 bg-slate-800 rounded-sm" />
          <div className="w-3 h-3 bg-emerald-900 rounded-sm" />
          <div className="w-3 h-3 bg-emerald-600 rounded-sm" />
          <div className="w-3 h-3 bg-emerald-400 rounded-sm" />
        </div>
        <span>More</span>
      </div>
    </div>
  );
};
