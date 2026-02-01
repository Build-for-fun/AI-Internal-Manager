import { Routes, Route } from 'react-router-dom'
import { useState } from 'react'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ChatInterface from './components/ChatInterface'
import KnowledgeGraph from './components/KnowledgeGraph'
import TeamAnalytics from './components/TeamAnalytics'
import Onboarding from './components/Onboarding'

function App() {
  const [voiceActive, setVoiceActive] = useState(false)

  return (
    <div className="scanline">
      <Layout voiceActive={voiceActive} setVoiceActive={setVoiceActive}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route
            path="/chat"
            element={<ChatInterface voiceActive={voiceActive} setVoiceActive={setVoiceActive} />}
          />
          <Route path="/knowledge" element={<KnowledgeGraph />} />
          <Route path="/analytics" element={<TeamAnalytics />} />
          <Route path="/onboarding" element={<Onboarding />} />
        </Routes>
      </Layout>
    </div>
  )
}

export default App
