const API_BASE = '/api/v1'

export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  const json = await res.json()
  return json.data as T
}
