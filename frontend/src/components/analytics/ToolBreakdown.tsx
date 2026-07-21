import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'OpenCode', tokens: 4000 },
  { name: 'Antigravity', tokens: 3000 },
  { name: 'VS Code', tokens: 2000 },
  { name: 'CLI', tokens: 1000 },
];

export const ToolBreakdown = () => {
  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Tool Breakdown</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
          <XAxis type="number" stroke="#94a3b8" />
          <YAxis dataKey="name" type="category" stroke="#94a3b8" />
          <Tooltip cursor={{ fill: '#334155' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
          <Legend />
          <Bar dataKey="tokens" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
