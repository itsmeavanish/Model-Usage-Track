import { useEffect, useState, useRef } from 'react';

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log("WS Connected");
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((prev) => [...prev.slice(-49), data]); // Keep last 50
      } catch (e) {
        console.error("Failed to parse message", e);
      }
    };

    ws.current.onclose = () => {
      console.log("WS Disconnected");
      setIsConnected(false);
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  return { messages, isConnected };
}
