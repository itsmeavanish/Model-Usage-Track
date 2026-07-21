import React, { useMemo } from 'react';
import { QuotaGauge } from './QuotaGauge';
import { ResetCountdown } from './ResetCountdown';

interface AccountOverviewProps {
  quotaData: any; // from WS or API
}

export const AccountOverview: React.FC<AccountOverviewProps> = ({ quotaData }) => {
  if (!quotaData || !quotaData.limits) {
    return (
      <div className="glass-panel p-6 w-full flex items-center justify-center min-h-[250px]">
        <p className="text-slate-400 animate-pulse">Waiting for quota data...</p>
      </div>
    );
  }

  const limits = quotaData.limits;

  return (
    <div className="glass-panel p-6 w-full">
      <div className="flex justify-between items-center border-b border-slate-700/50 pb-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Account Quota Overview</h2>
          <p className="text-sm text-slate-400">Official totals from Z.ai monitor endpoint</p>
        </div>
        <div className="bg-slate-800 px-3 py-1 rounded-full border border-slate-700">
          <span className="text-xs uppercase tracking-wider text-slate-300 font-semibold">Tier: <span className="text-emerald-400">{quotaData.level}</span></span>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-around gap-4">
        {limits.map((limit: any, idx: number) => (
          <div key={idx} className="flex flex-col items-center">
            <QuotaGauge percentage={limit.percentage} label={`${limit.window_label} Window`} />
            <div className="mt-4 bg-slate-800/50 rounded-lg px-4 py-2 border border-slate-700/50">
              <ResetCountdown targetDateStr={limit.next_reset_time} label="Resets in" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
