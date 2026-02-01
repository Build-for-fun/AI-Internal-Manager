import { ReactNode, useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  BarChart3,
  GraduationCap,
  Mic,
  MicOff,
  Settings,
  Bell,
  Search,
  ChevronRight,
} from 'lucide-react'
import { useRbac } from '../contexts/RbacContext'

interface LayoutProps {
  children: ReactNode
  voiceActive: boolean
  setVoiceActive: (active: boolean) => void
}

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  {
    path: '/chat',
    icon: MessageSquare,
    label: 'Chat',
    requiresAny: ['chat'],
  },
  {
    path: '/knowledge',
    icon: Network,
    label: 'Knowledge',
    requiresAny: [
      'knowledge_global',
      'knowledge_department',
      'knowledge_team',
      'knowledge_personal',
    ],
  },
  {
    path: '/analytics',
    icon: BarChart3,
    label: 'Analytics',
    requiresAny: ['team_analytics'],
  },
  {
    path: '/onboarding',
    icon: GraduationCap,
    label: 'Onboarding',
    requiresAny: ['onboarding_flows', 'onboarding_progress'],
  },
]

export default function Layout({ children, voiceActive, setVoiceActive }: LayoutProps) {
  const location = useLocation()
  const { loading, user, permissions, roleOverride, setRoleOverride } = useRbac()

  const allowedNavItems = useMemo(() => {
    if (loading) return navItems
    return navItems.filter((item) => {
      if (!item.requiresAny) return true
      return permissions.some((p) => item.requiresAny?.includes(p.resource))
    })
  }, [loading, permissions])

  const activeLabel = allowedNavItems.find((item) => item.path === location.pathname)?.label

  return (
    <div style={styles.container}>
      {/* Ambient background effects */}
      <div style={styles.ambientGlow} />
      <div style={styles.gridOverlay} className="grid-pattern" />

      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.logo}>
          <div style={styles.logoIcon}>
            <Network size={24} />
          </div>
          <span style={styles.logoText}>NEXUS</span>
        </div>

        <nav style={styles.nav}>
          {allowedNavItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <NavLink key={item.path} to={item.path} style={{ textDecoration: 'none' }}>
                <motion.div
                  style={{
                    ...styles.navItem,
                    ...(isActive ? styles.navItemActive : {}),
                  }}
                  whileHover={{ x: 4 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <item.icon size={20} style={{ opacity: isActive ? 1 : 0.6 }} />
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      style={styles.navIndicator}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                </motion.div>
              </NavLink>
            )
          })}
        </nav>

        {/* System Status */}
        <div style={styles.systemStatus}>
          <div style={styles.statusHeader}>
            <span style={styles.statusTitle}>SYSTEM STATUS</span>
            <div className="status-dot online" />
          </div>
          <div style={styles.statusItems}>
            <div style={styles.statusItem}>
              <span>API</span>
              <span style={{ color: 'var(--emerald)' }}>Operational</span>
            </div>
            <div style={styles.statusItem}>
              <span>Agents</span>
              <span style={{ color: 'var(--cyan)' }}>4 Active</span>
            </div>
            <div style={styles.statusItem}>
              <span>Memory</span>
              <span style={{ color: 'var(--text-secondary)' }}>2.4 GB</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div style={styles.main}>
        {/* Top bar */}
        <header style={styles.header}>
          <div style={styles.breadcrumb}>
            <span style={styles.breadcrumbText}>Mission Control</span>
            <ChevronRight size={14} style={{ opacity: 0.4 }} />
            <span style={styles.breadcrumbCurrent}>
              {activeLabel || 'Dashboard'}
            </span>
          </div>

          <div style={styles.headerActions}>
            {/* Search */}
            <div style={styles.searchContainer}>
              <Search size={16} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search knowledge base..."
                style={styles.searchInput}
              />
              <kbd style={styles.searchKbd}>⌘K</kbd>
            </div>

            {/* Role switcher */}
            <div style={styles.roleSwitcher}>
              <span style={styles.roleLabel}>Role</span>
              <select
                value={roleOverride || ''}
                onChange={(e) =>
                  setRoleOverride(e.target.value ? e.target.value : null)
                }
                style={styles.roleSelect}
              >
                <option value="">Auto</option>
                <option value="ceo">CEO</option>
                <option value="leadership">Leadership</option>
                <option value="manager">Manager</option>
                <option value="ic">IC</option>
                <option value="new_employee">Intern</option>
              </select>
            </div>

            {/* Voice toggle */}
            <motion.button
              style={{
                ...styles.iconButton,
                ...(voiceActive ? styles.iconButtonActive : {}),
              }}
              onClick={() => setVoiceActive(!voiceActive)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {voiceActive ? <Mic size={18} /> : <MicOff size={18} />}
              {voiceActive && <div style={styles.voicePulse} />}
            </motion.button>

            {/* Notifications */}
            <motion.button
              style={styles.iconButton}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Bell size={18} />
              <div style={styles.notificationDot} />
            </motion.button>

            {/* Settings */}
            <motion.button
              style={styles.iconButton}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Settings size={18} />
            </motion.button>

            {/* User avatar */}
            <div style={styles.userMeta}>
              <div style={styles.userAvatar}>
                <span>{user?.name?.slice(0, 2).toUpperCase() || 'AI'}</span>
              </div>
              <div style={styles.userInfo}>
                <span style={styles.userName}>{user?.name || 'Access Pending'}</span>
                <span style={styles.userRole}>{user?.role || '...'}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={styles.content}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              style={{ height: '100%' }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    minHeight: '100vh',
    position: 'relative',
    overflow: 'hidden',
  },
  ambientGlow: {
    position: 'fixed',
    top: '-50%',
    left: '-25%',
    width: '100%',
    height: '100%',
    background: 'radial-gradient(ellipse at center, rgba(123, 97, 255, 0.08) 0%, transparent 70%)',
    pointerEvents: 'none',
    zIndex: 0,
  },
  gridOverlay: {
    position: 'fixed',
    inset: 0,
    opacity: 0.3,
    pointerEvents: 'none',
    zIndex: 0,
  },
  sidebar: {
    width: '260px',
    background: 'linear-gradient(180deg, var(--surface) 0%, var(--abyss) 100%)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    padding: 'var(--space-lg)',
    position: 'relative',
    zIndex: 10,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    marginBottom: 'var(--space-2xl)',
    paddingLeft: 'var(--space-sm)',
  },
  logoIcon: {
    width: '40px',
    height: '40px',
    borderRadius: 'var(--radius-lg)',
    background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--void)',
  },
  logoText: {
    fontSize: '1.25rem',
    fontWeight: 700,
    letterSpacing: '0.1em',
    background: 'linear-gradient(135deg, var(--text-primary), var(--text-secondary))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xs)',
    flex: 1,
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    padding: 'var(--space-sm) var(--space-md)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    fontSize: '0.9375rem',
    fontWeight: 500,
    position: 'relative',
    transition: 'all var(--transition-fast)',
  },
  navItemActive: {
    color: 'var(--text-primary)',
    background: 'var(--elevated)',
  },
  navIndicator: {
    position: 'absolute',
    left: 0,
    top: '50%',
    transform: 'translateY(-50%)',
    width: '3px',
    height: '24px',
    borderRadius: 'var(--radius-full)',
    background: 'linear-gradient(180deg, var(--cyan), var(--violet))',
  },
  systemStatus: {
    marginTop: 'auto',
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border)',
  },
  statusHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-md)',
  },
  statusTitle: {
    fontSize: '0.6875rem',
    fontWeight: 600,
    letterSpacing: '0.1em',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
  },
  statusItems: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  statusItem: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.8125rem',
    color: 'var(--text-secondary)',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    zIndex: 10,
  },
  header: {
    height: '64px',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 var(--space-xl)',
    background: 'rgba(10, 10, 18, 0.8)',
    backdropFilter: 'blur(12px)',
  },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  breadcrumbText: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
  },
  breadcrumbCurrent: {
    fontSize: '0.875rem',
    color: 'var(--text-primary)',
    fontWeight: 500,
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
  },
  searchContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-sm) var(--space-md)',
    width: '280px',
  },
  searchInput: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontSize: '0.875rem',
  },
  searchKbd: {
    fontSize: '0.6875rem',
    padding: '2px 6px',
    borderRadius: 'var(--radius-sm)',
    background: 'var(--elevated)',
    color: 'var(--text-muted)',
    border: '1px solid var(--border)',
    fontFamily: 'var(--font-mono)',
  },
  roleSwitcher: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    padding: '6px 10px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    background: 'var(--surface)',
  },
  roleLabel: {
    fontSize: '0.6875rem',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
  },
  roleSelect: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: '0.8125rem',
    cursor: 'pointer',
    outline: 'none',
  },
  iconButton: {
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-secondary)',
    position: 'relative',
    cursor: 'pointer',
  },
  iconButtonActive: {
    background: 'var(--cyan-glow)',
    borderColor: 'var(--cyan)',
    color: 'var(--cyan)',
  },
  voicePulse: {
    position: 'absolute',
    inset: '-4px',
    borderRadius: 'var(--radius-lg)',
    border: '2px solid var(--cyan)',
    opacity: 0.5,
    animation: 'pulse-glow 1.5s ease-in-out infinite',
  },
  notificationDot: {
    position: 'absolute',
    top: '6px',
    right: '6px',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--rose)',
  },
  userAvatar: {
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-md)',
    background: 'linear-gradient(135deg, var(--violet), var(--cyan))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--void)',
  },
  userMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  userName: {
    fontSize: '0.8125rem',
    color: 'var(--text-primary)',
  },
  userRole: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  content: {
    flex: 1,
    padding: 'var(--space-xl)',
    overflowY: 'auto',
  },
}
