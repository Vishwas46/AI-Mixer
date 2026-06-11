// Central API client.
// In dev the Vite server proxies /api to the backend (see vite.config.js).
// Set VITE_API_BASE to call a backend on another host (e.g. a LAN machine).
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export const apiUrl = (path) => `${API_BASE}${path}`

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  // Only set a JSON content type for string bodies — FormData sets its own.
  if (typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(apiUrl(path), { ...options, headers })
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      // non-JSON error body
    }
    throw new Error(detail || `Request failed with status ${res.status}`)
  }
  return res.json()
}
