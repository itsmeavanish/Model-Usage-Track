import React, { useMemo, useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { AccountOverview } from './components/dashboard/AccountOverview';

function App() {
  const { messages, isConnected } = useWebSocket('ws://localhost:8000/api/v1/ws');
  const [quotaData, setQuotaData] = useState<any>(null);

  useEffect(() => {
    // Process new messages
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.type === 'quota_update') {
        setQuotaData(lastMessage.data);
      }
    }
  }, [messages]);

  // If no WS data yet, we should fetch from REST API, but for now we'll just wait for WS
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
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
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

      <main className="max-w-6xl mx-auto space-y-8">
        <AccountOverview quotaData={quotaData} />
        
        {/* Placeholder for other components to come in later milestones */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel p-6 min-h-[300px] flex items-center justify-center">
            <p className="text-slate-500">Live Request Feed (Coming Soon)</p>
          </div>
          <div className="glass-panel p-6 min-h-[300px] flex items-center justify-center">
            <p className="text-slate-500">Unattributed Usage (Coming Soon)</p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
