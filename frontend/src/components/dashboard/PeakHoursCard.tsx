import React from 'react';
import { Clock } from 'lucide-react';
import { useLiveData } from '../../hooks/useLiveData';
import { formatTokens, formatTokensFull } from '../../utils/format';

interface HourBucket {
  hour: number;
  tokens: number;
  requests: number;
}

interface PeakHours {
  days: number;
  timezone: string | null;
  hours: HourBucket[];
  peak: { hour: number; tokens: number; requests: number; share: number } | null;
  total_tokens: number;
}

const hourLabel = (h: number): string =>
  new Date(2026, 0, 1, h % 24).toLocaleTimeString([], { hour: 'numeric', hour12: true });

function barColor(tokens: number, max: number, isPeak: boolean): string {
  if (isPeak) return 'bg-orange-400';
  if (tokens <= 0 || max <= 0) return 'bg-slate-800';
  const ratio = tokens / max;
  if (ratio > 0.6) return 'bg-emerald-400';
  if (ratio > 0.3) return 'bg-emerald-600';
  return 'bg-emerald-900';
}

export const PeakHoursCard: React.FC = () => {
  const { data, loading } = useLiveData<PeakHours>('/analytics/peak-hours?days=7');

  const hours = data?.hours ?? [];
  const peak = data?.peak ?? null;
  const max = hours.reduce((m, h) => Math.max(m, h.tokens), 0);

  return (
    <div className="glass-panel p-6 bg-gradient-to-r from-cyan-500/10 to-emerald-500/10 border-cyan-500/20">
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-cyan-500/20 rounded-lg text-cyan-400">
          <Clock size={24} />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Peak Usage Hour</h3>
          {loading ? (
            <p className="text-sm text-slate-500 animate-pulse mt-1">Loading…</p>
          ) : peak ? (
            <>
              <p className="text-2xl font-bold text-white mt-1">
                {hourLabel(peak.hour)} – {hourLabel(peak.hour + 1)}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                <span className="font-semibold text-emerald-400" title={`${formatTokensFull(peak.tokens)} tokens`}>
                  {formatTokens(peak.tokens)} tokens
                </span>
                {' · '}{peak.share.toFixed(1)}% of last {data?.days ?? 7} days
                {data?.timezone ? ` · ${data.timezone}` : ''}
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500 mt-1">No usage recorded yet.</p>
          )}
        </div>
      </div>

      {peak && hours.length > 0 && (
        <div className="mt-4">
          <div className="flex items-end gap-[3px] h-16">
            {hours.map((h) => {
              const isPeak = peak.hour === h.hour;
              const heightPct = max > 0 ? Math.max((h.tokens / max) * 100, h.tokens > 0 ? 6 : 2) : 2;
              return (
                <div key={h.hour} className="relative flex-1 h-full group">
                  <div
                    className={`absolute inset-x-0 bottom-0 rounded-t-sm ${barColor(h.tokens, max, isPeak)}`}
                    style={{ height: `${heightPct}%`, minHeight: 2 }}
                  />
                  <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-slate-800 text-xs px-2 py-1 rounded text-nowrap border border-slate-700 z-10">
                    {hourLabel(h.hour)}: {formatTokensFull(h.tokens)} tokens ({h.requests} requests)
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-1.5 text-[10px] text-slate-500">
            <span>12 AM</span>
            <span>6 AM</span>
            <span>12 PM</span>
            <span>6 PM</span>
            <span>11 PM</span>
          </div>
        </div>
      )}
    </div>
  );
};
