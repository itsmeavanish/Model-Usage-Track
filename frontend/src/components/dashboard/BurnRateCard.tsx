import React from 'react';
import { Flame } from 'lucide-react';
import { useLiveData } from '../../hooks/useLiveData';

interface BurnRate {
  tokens_per_hour: number;
  window_minutes: number;
  window_label: string | null;
  estimated_exhaustion: string | null;
}

export const BurnRateCard: React.FC = () => {
  const { data } = useLiveData<BurnRate>('/analytics/burn-rate');

  const tokensPerHour = data?.tokens_per_hour || 0;
  const exhaustion = data?.estimated_exhaustion
    ? new Date(data.estimated_exhaustion).toLocaleString()
    : null;

  return (
    <div className="glass-panel p-6 flex items-center space-x-4 bg-gradient-to-r from-orange-500/10 to-red-500/10 border-orange-500/20">
      <div className="p-3 bg-orange-500/20 rounded-lg text-orange-400">
        <Flame size={24} />
      </div>
      <div>
        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Current Burn Rate</h3>
        <p className="text-2xl font-bold text-white mt-1">
          {tokensPerHour.toLocaleString()} <span className="text-sm font-normal text-slate-400">tokens/hr</span>
        </p>
        {exhaustion && (
          <p className="text-xs text-slate-400 mt-1">Est. exhaustion: {exhaustion}</p>
        )}
      </div>
    </div>
  );
};
