import React from 'react';
import { AlertCircle } from 'lucide-react';
import { useLiveData } from '../../hooks/useLiveData';

interface Unattributed {
  official_percentage: number | null;
  enriched_percentage: number;
  unattributed_percentage: number;
  status: string;
}

export const UnattributedBanner: React.FC = () => {
  const { data } = useLiveData<Unattributed>('/analytics/unattributed');
  const gap = data?.unattributed_percentage || 0;
  if (gap < 5) return null;

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-lg flex items-start space-x-3 mt-6">
      <AlertCircle className="text-amber-500 mt-0.5 flex-shrink-0" size={18} />
      <div>
        <h4 className="text-amber-400 font-medium">Unattributed Usage Detected</h4>
        <p className="text-amber-200/70 text-sm mt-1">
          {gap.toFixed(1)}% of the official Z.ai quota consumption cannot be traced back to local collectors.
          Check if a new tool is using your API key without being monitored.
        </p>
        {data && (
          <p className="text-amber-200/50 text-xs mt-1">
            Official {data.official_percentage?.toFixed(1)}% · Enriched {data.enriched_percentage.toFixed(1)}% · Status: {data.status}
          </p>
        )}
      </div>
    </div>
  );
};
