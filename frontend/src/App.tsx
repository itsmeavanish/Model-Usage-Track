import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { LiveRefreshContext } from './context/LiveRefresh';
import { AccountOverview } from './components/dashboard/AccountOverview';
import { BurnRateCard } from './components/dashboard/BurnRateCard';
import { PeakHoursCard } from './components/dashboard/PeakHoursCard';
import { UnattributedBanner } from './components/dashboard/UnattributedBanner';
import { UsageTrends } from './components/analytics/UsageTrends';
import { ModelBreakdown } from './components/analytics/ModelBreakdown';
import { ProviderBreakdown } from './components/analytics/ProviderBreakdown';
import { ToolBreakdown } from './components/analytics/ToolBreakdown';
import { HeatmapCalendar } from './components/analytics/HeatmapCalendar';
import { MeVsTotalCard } from './components/analytics/MeVsTotalCard';
import { RequestExplorer } from './components/explorer/RequestExplorer';
import { RefreshCw } from 'lucide-react';

function App() {
  const { messages, isConnected, status, reconnectCount, reconnect } = useWebSocket('ws://localhost:8000/api/v1/ws');
  const [quotaData, setQuotaData] = useState<any>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);

  const fetchQuotaData = useCallback(() => {
    fetch('http://localhost:8000/api/v1/quota/current')
      .then(res => res.json())
      .then(data => {
        if (!data.error) {
          setQuotaData(data);
        }
      })
      .catch(err => console.error("Failed to fetch current quota", err));
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.type === 'quota_update') {
        setQuotaData(lastMessage.data);
      }
      // Any live event bumps the refresh signal so analytics components re-fetch.
      if (lastMessage.type === 'quota_update' || lastMessage.type === 'new_request') {
        setRefreshSignal(s => s + 1);
      }
    }
  }, [messages]);

  useEffect(() => {
    // Fetch initial data or update on connection established
    fetchQuotaData();
  }, [fetchQuotaData, isConnected]);

  // Fallback: refresh analytics every 30s even if the WebSocket is down
  // (WS also auto-reconnects with exponential backoff — see useWebSocket.ts).
  useEffect(() => {
    const id = setInterval(() => setRefreshSignal(s => s + 1), 30000);
    return () => clearInterval(id);
  }, []);

  const getStatusBadge = () => {
    switch (status) {
      case 'connected':
        return (
          <div className="flex items-center space-x-2 bg-emerald-950/60 border border-emerald-800/60 px-3 py-1.5 rounded-full text-xs font-medium text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Live Status: Connected</span>
          </div>
        );
      case 'connecting':
        return (
          <div className="flex items-center space-x-2 bg-amber-950/60 border border-amber-800/60 px-3 py-1.5 rounded-full text-xs font-medium text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>Connecting...</span>
          </div>
        );
      case 'reconnecting':
        return (
          <div className="flex items-center space-x-2 bg-amber-950/60 border border-amber-800/60 px-3 py-1.5 rounded-full text-xs font-medium text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span>Reconnecting (retry #{reconnectCount})...</span>
            <button
              onClick={reconnect}
              title="Force reconnect"
              className="ml-1 p-0.5 hover:bg-amber-800/50 rounded transition-colors text-amber-300"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
        );
      case 'disconnected':
      default:
        return (
          <div className="flex items-center space-x-2 bg-rose-950/60 border border-rose-800/60 px-3 py-1.5 rounded-full text-xs font-medium text-rose-400">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Disconnected</span>
            <button
              onClick={reconnect}
              className="ml-1.5 px-2 py-0.5 bg-rose-900/80 hover:bg-rose-800 border border-rose-700 rounded text-rose-200 transition-colors flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        );
    }
  };

  return (
    <LiveRefreshContext.Provider value={{ signal: refreshSignal }}>
      <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
        <header className="mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
              Model Usage Monitor
            </h1>
            <p className="text-slate-400 mt-1">Z.ai · OpenAI · Anthropic — Account-Wide API Consumption</p>
          </div>
          <div>
            {getStatusBadge()}
          </div>
        </header>

        <main className="max-w-6xl mx-auto space-y-6">
          {/* Single continuous grid: a card's position must not depend on the
              other column's height. Splitting this into two grid rows made the
              shorter left column stretch to the right column's height, leaving
              a huge dead band between AccountOverview and MeVsTotalCard. */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <AccountOverview quotaData={quotaData} />
              <UnattributedBanner />
              <MeVsTotalCard />
              <UsageTrends />
            </div>
            <div className="space-y-6">
              <BurnRateCard />
              <PeakHoursCard />
              <ToolBreakdown />
              <ModelBreakdown />
              <ProviderBreakdown />
            </div>
          </div>

          <HeatmapCalendar />

          <div className="mt-8">
            <RequestExplorer />
          </div>
        </main>
      </div>
    </LiveRefreshContext.Provider>
  );
}

export default App;
