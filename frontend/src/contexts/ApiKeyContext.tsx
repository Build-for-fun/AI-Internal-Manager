import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'keywords_ai_api_key'

interface ApiKeyState {
  apiKey: string | null
  isAuthenticated: boolean
  setApiKey: (key: string) => void
  clearApiKey: () => void
}

const ApiKeyContext = createContext<ApiKeyState | null>(null)

export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY)
    } catch {
      return null
    }
  })

  const setApiKey = useCallback((key: string) => {
    try {
      localStorage.setItem(STORAGE_KEY, key)
    } catch {
      // localStorage unavailable
    }
    setApiKeyState(key)
  }, [])

  const clearApiKey = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // localStorage unavailable
    }
    setApiKeyState(null)
  }, [])

  // Sync with localStorage changes from other tabs
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setApiKeyState(e.newValue)
      }
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  const value: ApiKeyState = {
    apiKey,
    isAuthenticated: !!apiKey && apiKey.trim().length > 0,
    setApiKey,
    clearApiKey,
  }

  return <ApiKeyContext.Provider value={value}>{children}</ApiKeyContext.Provider>
}

export function useApiKey() {
  const context = useContext(ApiKeyContext)
  if (!context) {
    throw new Error('useApiKey must be used within ApiKeyProvider')
  }
  return context
}
