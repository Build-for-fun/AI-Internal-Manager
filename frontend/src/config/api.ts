// API configuration
// In development, Vite proxies /api to localhost:8000
// In production, set VITE_API_URL to your backend URL

export const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function apiUrl(path: string): string {
  // If path already starts with http, return as-is
  if (path.startsWith('http')) {
    return path
  }

  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  // In development (no VITE_API_URL), use relative paths (Vite proxy handles it)
  // In production, prepend the API base URL
  return `${API_BASE_URL}${normalizedPath}`
}

export function wsUrl(path: string): string {
  if (!API_BASE_URL) {
    // Development: use relative WebSocket path
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${path}`
  }

  // Production: convert API URL to WebSocket URL
  const wsBase = API_BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}${path}`
}
