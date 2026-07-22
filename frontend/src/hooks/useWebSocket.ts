import { useEffect, useState, useRef, useCallback } from 'react';

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<any[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [reconnectCount, setReconnectCount] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isManuallyClosed = useRef(false);

  const clearTimers = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  };

  const connect = useCallback(() => {
    clearTimers();
    isManuallyClosed.current = false;

    try {
      ws.current = new WebSocket(url);
      setStatus(prev => (prev === 'connected' || prev === 'connecting' ? 'connecting' : 'reconnecting'));

      ws.current.onopen = () => {
        console.log('WS Connected');
        setStatus('connected');
        setReconnectCount(0);

        // Start ping interval every 20 seconds
        pingIntervalRef.current = setInterval(() => {
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send('ping');
          }
        }, 20000);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') return;
          setMessages((prev) => [...prev.slice(-49), data]);
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.current.onclose = () => {
        console.log('WS Disconnected');
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        if (!isManuallyClosed.current) {
          setStatus('reconnecting');
          setReconnectCount((count) => {
            const nextCount = count + 1;
            // Exponential backoff: min 1s, max 10s
            const delay = Math.min(1000 * Math.pow(1.5, nextCount), 10000);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, delay);
            return nextCount;
          });
        } else {
          setStatus('disconnected');
        }
      };

      ws.current.onerror = (err) => {
        console.error('WS Error:', err);
      };
    } catch (err) {
      console.error('WS Connection initiation error:', err);
      setStatus('disconnected');
    }
  }, [url]);

  const reconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
    setReconnectCount(0);
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      isManuallyClosed.current = true;
      clearTimers();
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return {
    messages,
    isConnected: status === 'connected',
    status,
    reconnectCount,
    reconnect
  };
}
