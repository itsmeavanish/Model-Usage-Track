import React from 'react';
import { AlertCircle } from 'lucide-react';

interface UnattributedBannerProps {
  unattributedData?: any;
}

export const UnattributedBanner: React.FC<UnattributedBannerProps> = ({ unattributedData }) => {
  const gap = unattributedData?.unattributed_percentage || 0;
  
  if (gap < 5) return null; // Only show if gap is significant

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-lg flex items-start space-x-3 mt-6">
      <AlertCircle className="text-amber-500 mt-0.5 flex-shrink-0" size={18} />
      <div>
        <h4 className="text-amber-400 font-medium">Unattributed Usage Detected</h4>
        <p className="text-amber-200/70 text-sm mt-1">
          {gap}% of the official Z.ai quota consumption cannot be traced back to local collectors. 
          Check if a new tool is using your API key without being monitored.
        </p>
      </div>
    </div>
  );
};
