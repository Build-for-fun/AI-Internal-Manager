import { Routes, Route, Navigate } from 'react-router-dom'
import { useMemo, useState } from 'react'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ChatInterface from './components/ChatInterface'
import KnowledgeGraph from './components/KnowledgeGraph'
import TeamAnalytics from './components/TeamAnalytics'
import Onboarding from './components/Onboarding'
import { RbacProvider, useRbac } from './contexts/RbacContext'

function App() {
  const [voiceActive, setVoiceActive] = useState(false)

  return (
    <RbacProvider>
      <div className="scanline">
        <Layout voiceActive={voiceActive} setVoiceActive={setVoiceActive}>
          <AppRoutes voiceActive={voiceActive} setVoiceActive={setVoiceActive} />
        </Layout>
      </div>
    </RbacProvider>
  )
}

export default App

function AppRoutes({
  voiceActive,
  setVoiceActive,
}: {
  voiceActive: boolean
  setVoiceActive: (active: boolean) => void
}) {
  const { loading, error, permissions } = useRbac()

  const canViewAnalytics = useMemo(
    () => permissions.some((p) => p.resource === 'team_analytics'),
    [permissions]
  )
  const canViewChat = useMemo(
    () => permissions.some((p) => p.resource === 'chat'),
    [permissions]
  )
  const canViewKnowledge = useMemo(
    () =>
      permissions.some((p) =>
        [
          'knowledge_global',
          'knowledge_department',
          'knowledge_team',
          'knowledge_personal',
        ].includes(p.resource)
      ),
    [permissions]
  )
  const canViewOnboarding = useMemo(
    () =>
      permissions.some((p) =>
        ['onboarding_flows', 'onboarding_progress'].includes(p.resource)
      ),
    [permissions]
  )

  if (loading) {
    return (
      <div style={{ color: 'var(--text-secondary)' }}>Loading access profile…</div>
    )
  }

  if (error) {
    return (
      <div style={{ color: 'var(--rose)' }}>Failed to load access profile.</div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route
        path="/chat"
        element={
          canViewChat ? (
            <ChatInterface voiceActive={voiceActive} setVoiceActive={setVoiceActive} />
          ) : (
            <AccessDenied />
          )
        }
      />
      <Route
        path="/knowledge"
        element={canViewKnowledge ? <KnowledgeGraph /> : <AccessDenied />}
      />
      <Route
        path="/analytics"
        element={canViewAnalytics ? <TeamAnalytics /> : <AccessDenied />}
      />
      <Route
        path="/onboarding"
        element={canViewOnboarding ? <Onboarding /> : <AccessDenied />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function AccessDenied() {
  return (
    <div style={{ color: 'var(--text-secondary)' }}>
      You don’t have access to this area.
    </div>
  )
}
