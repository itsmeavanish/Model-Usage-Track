import { useContext, useEffect, useState } from 'react';
import { apiFetch } from '../api';
import { LiveRefreshContext } from '../context/LiveRefresh';

interface LiveDataResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch a JSON endpoint and automatically re-fetch whenever the live-refresh
 * signal changes (driven by WebSocket events: new_request / quota_update) or
 * the 30s fallback tick. Pass a stable `path` string.
 */
export function useLiveData<T>(path: string): LiveDataResult<T> {
  const { signal } = useContext(LiveRefreshContext);
  const [state, setState] = useState<LiveDataResult<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const json = await apiFetch<T>(path);
        if (!cancelled) setState({ data: json, loading: false, error: null });
      } catch (e) {
        // Preserve previously-fetched data on refetch errors so the UI does
        // not blank out on a transient failure or browser refresh.
        if (!cancelled) setState((prev) => ({ data: prev.data, loading: false, error: e as Error }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [path, signal]);

  return state;
}
