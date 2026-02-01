import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Brain,
  Network,
  Zap,
  Shield,
  MessagesSquare,
  BarChart3,
  Sparkles,
  ChevronDown
} from 'lucide-react'

export default function LandingPage() {
  return (
    <div style={styles.container}>
      {/* Animated background */}
      <div style={styles.bgGrid} />
      <div style={styles.bgOrb1} />
      <div style={styles.bgOrb2} />
      <div style={styles.bgOrb3} />
      <NeuralNetworkBg />

      {/* Navigation */}
      <motion.nav
        style={styles.nav}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <div style={styles.navInner}>
          <div style={styles.logo}>
            <div style={styles.logoIcon}>
              <Network size={22} />
            </div>
            <span style={styles.logoText}>NEXUS</span>
          </div>

          <div style={styles.navLinks}>
            <a href="#features" style={styles.navLink}>Features</a>
            <a href="#capabilities" style={styles.navLink}>Capabilities</a>
            <a href="#integration" style={styles.navLink}>Integration</a>
          </div>

          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <motion.button
              style={styles.dashboardBtn}
              whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(0, 245, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
            >
              Dashboard
              <ArrowRight size={16} />
            </motion.button>
          </Link>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section style={styles.hero}>
        <motion.div
          style={styles.heroContent}
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <motion.div
            style={styles.badge}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Sparkles size={14} style={{ color: 'var(--cyan)' }} />
            <span>AI-Powered Intelligence Layer</span>
          </motion.div>

          <h1 style={styles.heroTitle}>
            <span style={styles.heroTitleLine1}>Your Organization's</span>
            <span style={styles.heroTitleLine2}>
              <span className="text-gradient">Neural Cortex</span>
            </span>
          </h1>

          <p style={styles.heroSubtitle}>
            Transform institutional knowledge into actionable intelligence.
            Multi-agent orchestration meets enterprise memory —
            your team's collective wisdom, instantly accessible.
          </p>

          <div style={styles.heroCtas}>
            <Link to="/dashboard" style={{ textDecoration: 'none' }}>
              <motion.button
                style={styles.ctaPrimary}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                <Brain size={18} />
                Enter Mission Control
                <ArrowRight size={18} />
              </motion.button>
            </Link>
            <motion.button
              style={styles.ctaSecondary}
              whileHover={{ scale: 1.02, borderColor: 'var(--cyan)' }}
              whileTap={{ scale: 0.98 }}
            >
              Watch Demo
            </motion.button>
          </div>

          <div style={styles.heroStats}>
            <div style={styles.statItem}>
              <span style={styles.statValue}>4</span>
              <span style={styles.statLabel}>Active Agents</span>
            </div>
            <div style={styles.statDivider} />
            <div style={styles.statItem}>
              <span style={styles.statValue}>∞</span>
              <span style={styles.statLabel}>Memory Tiers</span>
            </div>
            <div style={styles.statDivider} />
            <div style={styles.statItem}>
              <span style={styles.statValue}>&lt;50ms</span>
              <span style={styles.statLabel}>Response Time</span>
            </div>
          </div>
        </motion.div>

        <motion.div
          style={styles.heroVisual}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
        >
          <HeroOrbital />
        </motion.div>

        <motion.div
          style={styles.scrollIndicator}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
        >
          <ChevronDown size={24} style={{ animation: 'bounce 2s infinite' }} />
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" style={styles.features}>
        <motion.div
          style={styles.sectionHeader}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span style={styles.sectionLabel}>CAPABILITIES</span>
          <h2 style={styles.sectionTitle}>Multi-Agent Intelligence</h2>
          <p style={styles.sectionSubtitle}>
            Specialized AI agents working in concert to serve every layer of your organization
          </p>
        </motion.div>

        <div style={styles.featureGrid}>
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              style={styles.featureCard}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -8, borderColor: feature.color }}
            >
              <div style={{ ...styles.featureIcon, background: feature.glow, borderColor: feature.color }}>
                <feature.icon size={24} style={{ color: feature.color }} />
              </div>
              <h3 style={styles.featureTitle}>{feature.title}</h3>
              <p style={styles.featureDesc}>{feature.description}</p>
              <div style={{ ...styles.featureAccent, background: feature.color }} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* Architecture Section */}
      <section id="capabilities" style={styles.architecture}>
        <div style={styles.archContent}>
          <motion.div
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <span style={styles.sectionLabel}>ARCHITECTURE</span>
            <h2 style={styles.archTitle}>
              Hierarchical Memory
              <span style={styles.archTitleAccent}> That Learns</span>
            </h2>
            <p style={styles.archDesc}>
              Four-tier memory hierarchy ensures context persistence across
              conversations, teams, and the entire organization. From ephemeral
              working memory to persistent institutional knowledge.
            </p>

            <div style={styles.memoryTiers}>
              {memoryTiers.map((tier, i) => (
                <motion.div
                  key={tier.name}
                  style={styles.memoryTier}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.1 }}
                >
                  <div style={{ ...styles.tierIndicator, background: tier.color }} />
                  <div style={styles.tierInfo}>
                    <span style={styles.tierName}>{tier.name}</span>
                    <span style={styles.tierDesc}>{tier.desc}</span>
                  </div>
                  <span style={{ ...styles.tierTtl, color: tier.color }}>{tier.ttl}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div
            style={styles.archVisual}
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <MemoryVisualization />
          </motion.div>
        </div>
      </section>

      {/* Integration Section */}
      <section id="integration" style={styles.integrations}>
        <motion.div
          style={styles.sectionHeader}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span style={styles.sectionLabel}>INTEGRATIONS</span>
          <h2 style={styles.sectionTitle}>Connected Intelligence</h2>
          <p style={styles.sectionSubtitle}>
            Seamlessly integrates with your existing tools through MCP connectors
          </p>
        </motion.div>

        <div style={styles.integrationLogos}>
          {['Jira', 'GitHub', 'Slack', 'Notion', 'Linear', 'Confluence'].map((name, i) => (
            <motion.div
              key={name}
              style={styles.integrationItem}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              whileHover={{ scale: 1.05, borderColor: 'var(--cyan)' }}
            >
              <span style={styles.integrationName}>{name}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section style={styles.finalCta}>
        <motion.div
          style={styles.ctaCard}
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 style={styles.ctaTitle}>Ready to Transform Your Team?</h2>
          <p style={styles.ctaSubtitle}>
            Deploy your organization's neural cortex and unlock collective intelligence
          </p>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <motion.button
              style={styles.ctaFinalBtn}
              whileHover={{ scale: 1.02, boxShadow: '0 0 60px rgba(0, 245, 212, 0.4)' }}
              whileTap={{ scale: 0.98 }}
            >
              <Network size={20} />
              Launch Dashboard
              <ArrowRight size={20} />
            </motion.button>
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer style={styles.footer}>
        <div style={styles.footerInner}>
          <div style={styles.footerLogo}>
            <Network size={18} />
            <span>NEXUS</span>
          </div>
          <span style={styles.footerText}>AI Internal Manager • Mission Control</span>
        </div>
      </footer>

      <style>{`
        @keyframes bounce {
          0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-10px); }
          60% { transform: translateY(-5px); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(1.5); opacity: 0; }
        }
        @keyframes rotate-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes dash {
          to { stroke-dashoffset: -1000; }
        }
      `}</style>
    </div>
  )
}

// Neural network background component
function NeuralNetworkBg() {
  return (
    <svg style={styles.neuralBg} viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="var(--violet)" stopOpacity="0.1" />
        </linearGradient>
      </defs>
      {/* Neural connection lines */}
      {[...Array(15)].map((_, i) => (
        <line
          key={i}
          x1={100 + Math.random() * 800}
          y1={100 + Math.random() * 800}
          x2={100 + Math.random() * 800}
          y2={100 + Math.random() * 800}
          stroke="url(#lineGrad)"
          strokeWidth="1"
          strokeDasharray="5,10"
          style={{ animation: `dash 20s linear infinite` }}
        />
      ))}
      {/* Nodes */}
      {[...Array(12)].map((_, i) => (
        <circle
          key={i}
          cx={100 + Math.random() * 800}
          cy={100 + Math.random() * 800}
          r={3 + Math.random() * 4}
          fill="var(--cyan)"
          opacity={0.2 + Math.random() * 0.3}
        />
      ))}
    </svg>
  )
}

// Hero orbital visualization
function HeroOrbital() {
  return (
    <div style={styles.orbital}>
      <div style={styles.orbitalCore}>
        <Brain size={48} style={{ color: 'var(--cyan)' }} />
      </div>
      <div style={{ ...styles.orbitalRing, animationDuration: '20s' }}>
        <div style={{ ...styles.orbitalNode, top: 0, left: '50%', transform: 'translate(-50%, -50%)' }}>
          <MessagesSquare size={16} />
        </div>
      </div>
      <div style={{ ...styles.orbitalRing, width: '300px', height: '300px', animationDuration: '30s', animationDirection: 'reverse' }}>
        <div style={{ ...styles.orbitalNode, bottom: 0, left: '50%', transform: 'translate(-50%, 50%)', background: 'var(--violet-glow)', borderColor: 'var(--violet)' }}>
          <Network size={16} style={{ color: 'var(--violet)' }} />
        </div>
      </div>
      <div style={{ ...styles.orbitalRing, width: '400px', height: '400px', animationDuration: '40s' }}>
        <div style={{ ...styles.orbitalNode, top: '50%', right: 0, transform: 'translate(50%, -50%)', background: 'var(--amber-glow)', borderColor: 'var(--amber)' }}>
          <BarChart3 size={16} style={{ color: 'var(--amber)' }} />
        </div>
      </div>
      <div style={styles.orbitalPulse} />
    </div>
  )
}

// Memory visualization component
function MemoryVisualization() {
  return (
    <div style={styles.memoryViz}>
      <div style={styles.memoryCore}>
        <div style={styles.memoryCoreInner}>
          <Shield size={32} style={{ color: 'var(--cyan)' }} />
        </div>
        <div style={styles.memoryCoreRing} />
      </div>
      {memoryTiers.map((tier, i) => (
        <div
          key={tier.name}
          style={{
            ...styles.memoryLayer,
            width: `${180 + i * 60}px`,
            height: `${180 + i * 60}px`,
            borderColor: tier.color,
            animationDelay: `${i * 0.5}s`,
          }}
        />
      ))}
    </div>
  )
}

const features = [
  {
    icon: Brain,
    title: 'Knowledge Agent',
    description: 'Hybrid search across Neo4j graph and Qdrant vectors for instant institutional knowledge retrieval',
    color: 'var(--cyan)',
    glow: 'var(--cyan-glow)',
  },
  {
    icon: MessagesSquare,
    title: 'Conversational AI',
    description: 'Natural language interface with voice support and real-time streaming responses',
    color: 'var(--violet)',
    glow: 'var(--violet-glow)',
  },
  {
    icon: BarChart3,
    title: 'Team Analytics',
    description: 'Deep insights from Jira, GitHub, and Slack through intelligent MCP connectors',
    color: 'var(--amber)',
    glow: 'var(--amber-glow)',
  },
  {
    icon: Zap,
    title: 'Smart Onboarding',
    description: 'Role-specific flows that accelerate new team members to full productivity',
    color: 'var(--emerald)',
    glow: 'var(--emerald-glow)',
  },
]

const memoryTiers = [
  { name: 'Short-term', desc: 'Active conversation context', ttl: '1 hour', color: 'var(--cyan)' },
  { name: 'User', desc: 'Individual preferences & history', ttl: 'Persistent', color: 'var(--violet)' },
  { name: 'Team', desc: 'Team decisions and norms', ttl: 'Persistent', color: 'var(--amber)' },
  { name: 'Organization', desc: 'Company policies & practices', ttl: 'Persistent', color: 'var(--rose)' },
]

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    background: 'var(--void)',
    position: 'relative',
    overflow: 'hidden',
  },
  bgGrid: {
    position: 'fixed',
    inset: 0,
    backgroundImage: `
      linear-gradient(rgba(37, 37, 56, 0.3) 1px, transparent 1px),
      linear-gradient(90deg, rgba(37, 37, 56, 0.3) 1px, transparent 1px)
    `,
    backgroundSize: '60px 60px',
    maskImage: 'radial-gradient(ellipse at center, black 0%, transparent 70%)',
    WebkitMaskImage: 'radial-gradient(ellipse at center, black 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  bgOrb1: {
    position: 'fixed',
    top: '-20%',
    right: '-10%',
    width: '800px',
    height: '800px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(123, 97, 255, 0.15) 0%, transparent 60%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  },
  bgOrb2: {
    position: 'fixed',
    bottom: '-20%',
    left: '-10%',
    width: '600px',
    height: '600px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(0, 245, 212, 0.12) 0%, transparent 60%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  },
  bgOrb3: {
    position: 'fixed',
    top: '40%',
    left: '30%',
    width: '400px',
    height: '400px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(255, 107, 157, 0.08) 0%, transparent 60%)',
    filter: 'blur(80px)',
    pointerEvents: 'none',
  },
  neuralBg: {
    position: 'fixed',
    inset: 0,
    width: '100%',
    height: '100%',
    opacity: 0.4,
    pointerEvents: 'none',
  },
  nav: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    padding: '20px 40px',
    background: 'linear-gradient(180deg, rgba(5, 5, 10, 0.9) 0%, transparent 100%)',
  },
  navInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoIcon: {
    width: '44px',
    height: '44px',
    borderRadius: '12px',
    background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--void)',
  },
  logoText: {
    fontSize: '1.5rem',
    fontWeight: 700,
    letterSpacing: '0.15em',
    background: 'linear-gradient(135deg, var(--text-primary), var(--text-secondary))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  navLinks: {
    display: 'flex',
    gap: '40px',
  },
  navLink: {
    fontSize: '0.9375rem',
    color: 'var(--text-secondary)',
    textDecoration: 'none',
    transition: 'color 0.2s',
    fontWeight: 500,
  },
  dashboardBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 24px',
    background: 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
    color: 'var(--void)',
    border: 'none',
    borderRadius: '10px',
    fontSize: '0.9375rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'var(--font-display)',
  },
  hero: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '140px 80px 80px',
    maxWidth: '1600px',
    margin: '0 auto',
    position: 'relative',
  },
  heroContent: {
    flex: 1,
    maxWidth: '700px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    background: 'rgba(0, 245, 212, 0.08)',
    border: '1px solid rgba(0, 245, 212, 0.2)',
    borderRadius: '100px',
    fontSize: '0.8125rem',
    color: 'var(--text-secondary)',
    marginBottom: '32px',
  },
  heroTitle: {
    fontSize: '4.5rem',
    fontWeight: 700,
    lineHeight: 1.05,
    marginBottom: '32px',
    letterSpacing: '-0.02em',
  },
  heroTitleLine1: {
    display: 'block',
    color: 'var(--text-primary)',
  },
  heroTitleLine2: {
    display: 'block',
  },
  heroSubtitle: {
    fontSize: '1.25rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.7,
    marginBottom: '48px',
    maxWidth: '560px',
  },
  heroCtas: {
    display: 'flex',
    gap: '16px',
    marginBottom: '64px',
  },
  ctaPrimary: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '16px 32px',
    background: 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
    color: 'var(--void)',
    border: 'none',
    borderRadius: '12px',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'var(--font-display)',
    boxShadow: '0 0 40px rgba(0, 245, 212, 0.3)',
  },
  ctaSecondary: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '16px 32px',
    background: 'transparent',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    fontSize: '1rem',
    fontWeight: 500,
    cursor: 'pointer',
    fontFamily: 'var(--font-display)',
    transition: 'all 0.2s',
  },
  heroStats: {
    display: 'flex',
    alignItems: 'center',
    gap: '40px',
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  statValue: {
    fontSize: '2rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
    background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  statLabel: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  statDivider: {
    width: '1px',
    height: '48px',
    background: 'var(--border)',
  },
  heroVisual: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  orbital: {
    position: 'relative',
    width: '500px',
    height: '500px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  orbitalCore: {
    width: '120px',
    height: '120px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, rgba(0, 245, 212, 0.15), rgba(123, 97, 255, 0.15))',
    border: '1px solid rgba(0, 245, 212, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    zIndex: 2,
    boxShadow: '0 0 60px rgba(0, 245, 212, 0.3)',
  },
  orbitalRing: {
    position: 'absolute',
    width: '200px',
    height: '200px',
    borderRadius: '50%',
    border: '1px dashed rgba(0, 245, 212, 0.3)',
    animation: 'rotate-slow 20s linear infinite',
  },
  orbitalNode: {
    position: 'absolute',
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: 'var(--cyan-glow)',
    border: '1px solid var(--cyan)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--cyan)',
  },
  orbitalPulse: {
    position: 'absolute',
    width: '120px',
    height: '120px',
    borderRadius: '50%',
    border: '2px solid var(--cyan)',
    animation: 'pulse-ring 2s ease-out infinite',
    opacity: 0.5,
  },
  scrollIndicator: {
    position: 'absolute',
    bottom: '40px',
    left: '50%',
    transform: 'translateX(-50%)',
    color: 'var(--text-muted)',
  },
  features: {
    padding: '120px 80px',
    maxWidth: '1400px',
    margin: '0 auto',
  },
  sectionHeader: {
    textAlign: 'center',
    marginBottom: '80px',
  },
  sectionLabel: {
    fontSize: '0.75rem',
    fontWeight: 600,
    letterSpacing: '0.2em',
    color: 'var(--cyan)',
    marginBottom: '16px',
    display: 'block',
  },
  sectionTitle: {
    fontSize: '3rem',
    fontWeight: 700,
    marginBottom: '20px',
    letterSpacing: '-0.01em',
  },
  sectionSubtitle: {
    fontSize: '1.125rem',
    color: 'var(--text-secondary)',
    maxWidth: '600px',
    margin: '0 auto',
  },
  featureGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '24px',
  },
  featureCard: {
    background: 'linear-gradient(180deg, var(--surface) 0%, var(--abyss) 100%)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    padding: '40px 32px',
    position: 'relative',
    overflow: 'hidden',
    transition: 'all 0.3s',
  },
  featureIcon: {
    width: '56px',
    height: '56px',
    borderRadius: '16px',
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  featureTitle: {
    fontSize: '1.25rem',
    fontWeight: 600,
    marginBottom: '12px',
  },
  featureDesc: {
    fontSize: '0.9375rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
  featureAccent: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '3px',
    opacity: 0.6,
  },
  architecture: {
    padding: '120px 80px',
    background: 'linear-gradient(180deg, transparent 0%, rgba(123, 97, 255, 0.03) 50%, transparent 100%)',
  },
  archContent: {
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    gap: '80px',
  },
  archTitle: {
    fontSize: '2.75rem',
    fontWeight: 700,
    marginBottom: '24px',
    lineHeight: 1.2,
  },
  archTitleAccent: {
    background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  archDesc: {
    fontSize: '1.125rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.7,
    marginBottom: '48px',
    maxWidth: '500px',
  },
  memoryTiers: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  memoryTier: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px 20px',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
  },
  tierIndicator: {
    width: '4px',
    height: '40px',
    borderRadius: '4px',
  },
  tierInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  tierName: {
    fontSize: '1rem',
    fontWeight: 600,
  },
  tierDesc: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
  },
  tierTtl: {
    fontSize: '0.75rem',
    fontWeight: 600,
    fontFamily: 'var(--font-mono)',
  },
  archVisual: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  memoryViz: {
    position: 'relative',
    width: '420px',
    height: '420px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  memoryCore: {
    position: 'relative',
    width: '100px',
    height: '100px',
    zIndex: 2,
  },
  memoryCoreInner: {
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, var(--surface), var(--abyss))',
    border: '2px solid var(--cyan)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 40px rgba(0, 245, 212, 0.3)',
  },
  memoryCoreRing: {
    position: 'absolute',
    inset: '-8px',
    borderRadius: '50%',
    border: '1px dashed var(--cyan)',
    animation: 'rotate-slow 10s linear infinite reverse',
  },
  memoryLayer: {
    position: 'absolute',
    borderRadius: '50%',
    border: '1px solid',
    opacity: 0.4,
    animation: 'pulse-ring 4s ease-out infinite',
  },
  integrations: {
    padding: '120px 80px',
    maxWidth: '1400px',
    margin: '0 auto',
  },
  integrationLogos: {
    display: 'flex',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: '20px',
  },
  integrationItem: {
    padding: '24px 48px',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    transition: 'all 0.3s',
  },
  integrationName: {
    fontSize: '1.125rem',
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  finalCta: {
    padding: '120px 80px',
  },
  ctaCard: {
    maxWidth: '900px',
    margin: '0 auto',
    textAlign: 'center',
    padding: '80px',
    background: 'linear-gradient(135deg, rgba(123, 97, 255, 0.1), rgba(0, 245, 212, 0.1))',
    border: '1px solid var(--border)',
    borderRadius: '32px',
    position: 'relative',
    overflow: 'hidden',
  },
  ctaTitle: {
    fontSize: '2.5rem',
    fontWeight: 700,
    marginBottom: '16px',
  },
  ctaSubtitle: {
    fontSize: '1.125rem',
    color: 'var(--text-secondary)',
    marginBottom: '40px',
  },
  ctaFinalBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '12px',
    padding: '20px 40px',
    background: 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
    color: 'var(--void)',
    border: 'none',
    borderRadius: '14px',
    fontSize: '1.125rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'var(--font-display)',
    boxShadow: '0 0 50px rgba(0, 245, 212, 0.35)',
  },
  footer: {
    padding: '40px 80px',
    borderTop: '1px solid var(--border)',
  },
  footerInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  footerLogo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: 'var(--text-secondary)',
    fontWeight: 600,
    letterSpacing: '0.1em',
  },
  footerText: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
  },
}
