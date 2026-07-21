import React, { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { AccountOverview } from './components/dashboard/AccountOverview';
import { BurnRateCard } from './components/dashboard/BurnRateCard';
import { UnattributedBanner } from './components/dashboard/UnattributedBanner';
import { UsageTrends } from './components/analytics/UsageTrends';
import { ModelBreakdown } from './components/analytics/ModelBreakdown';
import { ToolBreakdown } from './components/analytics/ToolBreakdown';
import { HeatmapCalendar } from './components/analytics/HeatmapCalendar';

function App() {
  const { messages, isConnected } = useWebSocket('ws://localhost:8000/api/v1/ws');
  const [quotaData, setQuotaData] = useState<any>(null);

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.type === 'quota_update') {
        setQuotaData(lastMessage.data);
      }
    }
  }, [messages]);

  useEffect(() => {
    if (!quotaData) {
      fetch('http://localhost:8000/api/v1/quota/current')
        .then(res => res.json())
        .then(data => {
          if (!data.error) {
            setQuotaData(data);
          }
        })
        .catch(err => console.error("Failed to fetch initial quota", err));
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <header className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
            GLM Usage Monitor
          </h1>
          <p className="text-slate-400 mt-1">Account-Wide Z.ai API Consumption</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-slate-400">Live Status:</span>
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm font-medium text-slate-300">{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <AccountOverview quotaData={quotaData} />
            <UnattributedBanner unattributedData={{ unattributed_percentage: 17.0 }} />
          </div>
          <div className="flex flex-col space-y-6">
            <BurnRateCard burnRateData={{ tokens_per_hour: 15000 }} />
            <ToolBreakdown />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <UsageTrends />
          </div>
          <div>
            <ModelBreakdown />
          </div>
        </div>
        
        <HeatmapCalendar />
      </main>
    </div>
  );
}

export default App;
