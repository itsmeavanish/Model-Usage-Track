import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const data = [
  { name: 'glm-5.2', value: 400 },
  { name: 'glm-5.2-flash', value: 300 },
  { name: 'glm-4-plus', value: 300 },
  { name: 'glm-vision', value: 200 },
];

const COLORS = ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b'];

export const ModelBreakdown = () => {
  return (
    <div className="glass-panel p-6 w-full h-[300px]">
      <h3 className="text-lg font-semibold mb-4">Model Breakdown</h3>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
