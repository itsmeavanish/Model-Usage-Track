import React from 'react';

// Simplified representation of a GitHub-style heatmap for usage intensity
export const HeatmapCalendar = () => {
  return (
    <div className="glass-panel p-6 w-full">
      <h3 className="text-lg font-semibold mb-4">Daily Activity Intensity</h3>
      <div className="flex space-x-1 items-end h-24 overflow-x-auto pb-2">
        {Array.from({ length: 30 }).map((_, i) => {
          const intensity = Math.random(); // 0 to 1
          let color = 'bg-slate-800'; // None
          if (intensity > 0.2) color = 'bg-emerald-900'; // Low
          if (intensity > 0.5) color = 'bg-emerald-600'; // Med
          if (intensity > 0.8) color = 'bg-emerald-400'; // High
          
          return (
            <div key={i} className="flex flex-col items-center group relative cursor-pointer">
              <div className={`w-4 h-4 rounded-sm ${color}`} />
              {/* Tooltip */}
              <div className="hidden group-hover:block absolute bottom-full mb-2 bg-slate-800 text-xs px-2 py-1 rounded text-nowrap border border-slate-700 z-10">
                Day {i + 1}: {Math.round(intensity * 10000)} tokens
              </div>
            </div>
          );
        })}
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
