import React from 'react';
import { Flame } from 'lucide-react';

interface BurnRateCardProps {
  burnRateData?: any;
}

export const BurnRateCard: React.FC<BurnRateCardProps> = ({ burnRateData }) => {
  const tokensPerHour = burnRateData?.tokens_per_hour || 0;
  
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
      </div>
    </div>
  );
};
