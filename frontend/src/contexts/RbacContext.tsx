import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiUrl } from '../config/api'

interface RbacUser {
  id: string
  name?: string | null
  email?: string | null
  role: string
  team_id?: string | null
  department_id?: string | null
  organization_id?: string | null
}

interface DashboardConfig {
  widgets: string[]
  data_scope: Record<string, string | number | boolean>
  refresh_interval: number
}

interface RbacBootstrap {
  user: RbacUser
  dashboard: DashboardConfig
  mcp_permissions: Record<string, { allowed: boolean; scope: Record<string, unknown>; level: string }>
  knowledge_scope: Record<string, unknown>
  permissions: Array<{
    resource: string
    access_level: string
    conditions: Record<string, unknown>
    description?: string
  }>
}

interface RbacState {
  loading: boolean
  error: string | null
  user: RbacUser | null
  dashboard: DashboardConfig | null
  permissions: RbacBootstrap['permissions']
  mcpPermissions: RbacBootstrap['mcp_permissions']
  knowledgeScope: RbacBootstrap['knowledge_scope']
  roleOverride: string | null
  setRoleOverride: (role: string | null) => void
  canAccess: (resource: string) => boolean
}

const RbacContext = createContext<RbacState | null>(null)

export function RbacProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bootstrap, setBootstrap] = useState<RbacBootstrap | null>(null)
  const [roleOverride, setRoleOverrideState] = useState<string | null>(
    () => localStorage.getItem('rbac_role')
  )

  useEffect(() => {
    let isMounted = true

    const loadBootstrap = async () => {
      try {
        const response = await fetch(apiUrl('/api/v1/rbac/bootstrap'), {
          headers: roleOverride ? { 'X-Demo-Role': roleOverride } : undefined,
        })
        if (!response.ok) {
          throw new Error(`Failed to load RBAC: ${response.status}`)
        }
        const data = (await response.json()) as RbacBootstrap
        if (isMounted) {
          setBootstrap(data)
          setError(null)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load RBAC')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadBootstrap()

    return () => {
      isMounted = false
    }
  }, [roleOverride])

  const setRoleOverride = (role: string | null) => {
    if (!role) {
      localStorage.removeItem('rbac_role')
      setRoleOverrideState(null)
      return
    }
    localStorage.setItem('rbac_role', role)
    setRoleOverrideState(role)
  }

  const permissions = bootstrap?.permissions ?? []

  const value = useMemo<RbacState>(
    () => ({
      loading,
      error,
      user: bootstrap?.user ?? null,
      dashboard: bootstrap?.dashboard ?? null,
      permissions,
      mcpPermissions: bootstrap?.mcp_permissions ?? {},
      knowledgeScope: bootstrap?.knowledge_scope ?? {},
      roleOverride,
      setRoleOverride,
      canAccess: (resource: string) => permissions.some((p) => p.resource === resource),
    }),
    [loading, error, bootstrap, permissions, roleOverride]
  )

  return <RbacContext.Provider value={value}>{children}</RbacContext.Provider>
}

export function useRbac() {
  const context = useContext(RbacContext)
  if (!context) {
    throw new Error('useRbac must be used within RbacProvider')
  }
  return context
}
