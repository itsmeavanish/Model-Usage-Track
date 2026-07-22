import { createContext } from 'react';

interface LiveRefreshValue {
  signal: number;
}

export const LiveRefreshContext = createContext<LiveRefreshValue>({ signal: 0 });
