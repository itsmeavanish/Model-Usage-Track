import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface QuotaGaugeProps {
  percentage: number;
  label: string;
}

export const QuotaGauge: React.FC<QuotaGaugeProps> = ({ percentage, label }) => {
  const data = [
    { name: 'Used', value: percentage },
    { name: 'Remaining', value: 100 - percentage },
  ];
  
  // Color scales based on usage
  let color = '#10b981'; // green
  if (percentage > 75) color = '#eab308'; // yellow
  if (percentage > 90) color = '#ef4444'; // red

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="relative w-32 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={60}
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              stroke="none"
            >
              <Cell key="cell-0" fill={color} />
              <Cell key="cell-1" fill="#334155" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold">{Math.round(percentage)}%</span>
        </div>
      </div>
      <span className="mt-2 text-sm text-slate-400 font-medium uppercase tracking-wider">{label}</span>
    </div>
  );
};
