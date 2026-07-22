const BASE_URL = 'http://localhost:8000/api/v1';

export async function apiFetch<T = any>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

export const API_BASE = BASE_URL;
