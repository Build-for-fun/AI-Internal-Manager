import { motion } from 'framer-motion'
import {
  Activity,
  Users,
  BookOpen,
  MessageSquare,
  TrendingUp,
  Clock,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'

const activityData = [
  { time: '00:00', queries: 12, agents: 4 },
  { time: '04:00', queries: 8, agents: 2 },
  { time: '08:00', queries: 45, agents: 8 },
  { time: '12:00', queries: 78, agents: 12 },
  { time: '16:00', queries: 92, agents: 15 },
  { time: '20:00', queries: 56, agents: 10 },
  { time: '23:59', queries: 34, agents: 6 },
]

const recentConversations = [
  {
    id: 1,
    agent: 'Knowledge Agent',
    query: 'What are our Q4 OKRs for the platform team?',
    time: '2 min ago',
    status: 'completed',
  },
  {
    id: 2,
    agent: 'Team Analysis',
    query: 'Show sprint velocity trends for Backend team',
    time: '8 min ago',
    status: 'completed',
  },
  {
    id: 3,
    agent: 'Onboarding',
    query: 'New hire checklist for Sarah Chen',
    time: '15 min ago',
    status: 'in_progress',
  },
  {
    id: 4,
    agent: 'Knowledge Agent',
    query: 'Find documentation about auth service',
    time: '23 min ago',
    status: 'completed',
  },
]

const teamHealth = [
  { team: 'Platform', health: 94, trend: 'up', change: '+3%' },
  { team: 'Backend', health: 87, trend: 'up', change: '+1%' },
  { team: 'Frontend', health: 78, trend: 'down', change: '-2%' },
  { team: 'DevOps', health: 91, trend: 'up', change: '+5%' },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export default function Dashboard() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={styles.container}
    >
      {/* Stats row */}
      <div style={styles.statsGrid}>
        <StatCard
          icon={MessageSquare}
          label="Conversations Today"
          value="247"
          change="+12%"
          trend="up"
          color="cyan"
        />
        <StatCard
          icon={Users}
          label="Active Users"
          value="89"
          change="+5%"
          trend="up"
          color="violet"
        />
        <StatCard
          icon={BookOpen}
          label="Knowledge Nodes"
          value="12,847"
          change="+234"
          trend="up"
          color="amber"
        />
        <StatCard
          icon={Zap}
          label="Avg Response Time"
          value="1.2s"
          change="-0.3s"
          trend="up"
          color="emerald"
        />
      </div>

      {/* Main grid */}
      <div style={styles.mainGrid}>
        {/* Activity chart */}
        <motion.div variants={itemVariants} style={styles.chartCard}>
          <div style={styles.cardHeader}>
            <div>
              <h3 style={styles.cardTitle}>System Activity</h3>
              <p style={styles.cardSubtitle}>Queries and agent activity over 24h</p>
            </div>
            <div style={styles.chartLegend}>
              <span style={styles.legendItem}>
                <span style={{ ...styles.legendDot, background: 'var(--cyan)' }} />
                Queries
              </span>
              <span style={styles.legendItem}>
                <span style={{ ...styles.legendDot, background: 'var(--violet)' }} />
                Agents
              </span>
            </div>
          </div>
          <div style={styles.chartContainer}>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="queriesGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00f5d4" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#00f5d4" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="agentsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7b61ff" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#7b61ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="time"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#606078', fontSize: 11 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#606078', fontSize: 11 }}
                  width={30}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1a1a2e',
                    border: '1px solid #252538',
                    borderRadius: '8px',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                  }}
                  labelStyle={{ color: '#f0f0f5' }}
                />
                <Area
                  type="monotone"
                  dataKey="queries"
                  stroke="#00f5d4"
                  strokeWidth={2}
                  fill="url(#queriesGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="agents"
                  stroke="#7b61ff"
                  strokeWidth={2}
                  fill="url(#agentsGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Recent conversations */}
        <motion.div variants={itemVariants} style={styles.conversationsCard}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Recent Conversations</h3>
            <button style={styles.viewAllBtn}>View all</button>
          </div>
          <div style={styles.conversationsList}>
            {recentConversations.map((conv) => (
              <motion.div
                key={conv.id}
                style={styles.conversationItem}
                whileHover={{ x: 4, background: 'var(--elevated)' }}
              >
                <div style={styles.conversationAgent}>
                  <div
                    style={{
                      ...styles.agentDot,
                      background:
                        conv.agent === 'Knowledge Agent'
                          ? 'var(--cyan)'
                          : conv.agent === 'Team Analysis'
                          ? 'var(--violet)'
                          : 'var(--amber)',
                    }}
                  />
                  <span style={styles.agentName}>{conv.agent}</span>
                </div>
                <p style={styles.conversationQuery}>{conv.query}</p>
                <div style={styles.conversationMeta}>
                  <span style={styles.conversationTime}>
                    <Clock size={12} />
                    {conv.time}
                  </span>
                  <span
                    className={`badge ${conv.status === 'completed' ? 'cyan' : 'amber'}`}
                    style={{ fontSize: '0.6875rem' }}
                  >
                    {conv.status === 'completed' ? 'Completed' : 'In Progress'}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Team health */}
        <motion.div variants={itemVariants} style={styles.healthCard}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>Team Health</h3>
            <span className="badge violet">Live</span>
          </div>
          <div style={styles.healthList}>
            {teamHealth.map((team) => (
              <div key={team.team} style={styles.healthItem}>
                <div style={styles.healthInfo}>
                  <span style={styles.healthTeam}>{team.team}</span>
                  <span
                    style={{
                      ...styles.healthChange,
                      color: team.trend === 'up' ? 'var(--emerald)' : 'var(--rose)',
                    }}
                  >
                    {team.trend === 'up' ? (
                      <ArrowUpRight size={14} />
                    ) : (
                      <ArrowDownRight size={14} />
                    )}
                    {team.change}
                  </span>
                </div>
                <div style={styles.healthBarContainer}>
                  <motion.div
                    style={{
                      ...styles.healthBar,
                      background:
                        team.health >= 90
                          ? 'var(--emerald)'
                          : team.health >= 80
                          ? 'var(--cyan)'
                          : team.health >= 70
                          ? 'var(--amber)'
                          : 'var(--rose)',
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${team.health}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                  />
                </div>
                <span style={styles.healthScore}>{team.health}%</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Quick actions */}
        <motion.div variants={itemVariants} style={styles.actionsCard}>
          <h3 style={styles.cardTitle}>Quick Actions</h3>
          <div style={styles.actionsGrid}>
            <QuickAction icon={MessageSquare} label="New Chat" color="cyan" />
            <QuickAction icon={BookOpen} label="Add Knowledge" color="violet" />
            <QuickAction icon={Users} label="Team Report" color="amber" />
            <QuickAction icon={Activity} label="System Logs" color="emerald" />
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  change,
  trend,
  color,
}: {
  icon: typeof Activity
  label: string
  value: string
  change: string
  trend: 'up' | 'down'
  color: 'cyan' | 'violet' | 'amber' | 'emerald'
}) {
  const colorMap = {
    cyan: { bg: 'var(--cyan-glow)', border: 'rgba(0, 245, 212, 0.3)', text: 'var(--cyan)' },
    violet: { bg: 'var(--violet-glow)', border: 'rgba(123, 97, 255, 0.3)', text: 'var(--violet)' },
    amber: { bg: 'var(--amber-glow)', border: 'rgba(255, 200, 87, 0.3)', text: 'var(--amber)' },
    emerald: {
      bg: 'var(--emerald-glow)',
      border: 'rgba(16, 185, 129, 0.3)',
      text: 'var(--emerald)',
    },
  }

  return (
    <motion.div
      variants={itemVariants}
      style={styles.statCard}
      whileHover={{ y: -4, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}
    >
      <div
        style={{
          ...styles.statIcon,
          background: colorMap[color].bg,
          border: `1px solid ${colorMap[color].border}`,
        }}
      >
        <Icon size={20} style={{ color: colorMap[color].text }} />
      </div>
      <div style={styles.statContent}>
        <span style={styles.statLabel}>{label}</span>
        <div style={styles.statValue}>
          <span>{value}</span>
          <span
            style={{
              ...styles.statChange,
              color: trend === 'up' ? 'var(--emerald)' : 'var(--rose)',
            }}
          >
            {trend === 'up' ? <TrendingUp size={14} /> : <ArrowDownRight size={14} />}
            {change}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

function QuickAction({
  icon: Icon,
  label,
  color,
}: {
  icon: typeof Activity
  label: string
  color: string
}) {
  return (
    <motion.button
      style={styles.quickAction}
      whileHover={{ scale: 1.02, borderColor: `var(--${color})` }}
      whileTap={{ scale: 0.98 }}
    >
      <Icon size={20} style={{ color: `var(--${color})` }} />
      <span>{label}</span>
    </motion.button>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xl)',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 'var(--space-lg)',
  },
  statCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
    display: 'flex',
    gap: 'var(--space-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-base)',
  },
  statIcon: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  statContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xs)',
  },
  statLabel: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
  },
  statValue: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    fontSize: '1.5rem',
    fontWeight: 600,
  },
  statChange: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
    fontSize: '0.75rem',
    fontWeight: 500,
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gridTemplateRows: 'auto auto',
    gap: 'var(--space-lg)',
  },
  chartCard: {
    gridColumn: '1',
    gridRow: '1 / 2',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-lg)',
  },
  cardTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-xs)',
  },
  cardSubtitle: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
  },
  chartLegend: {
    display: 'flex',
    gap: 'var(--space-md)',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  chartContainer: {
    marginLeft: '-10px',
  },
  conversationsCard: {
    gridColumn: '2',
    gridRow: '1 / 3',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
    display: 'flex',
    flexDirection: 'column',
  },
  viewAllBtn: {
    fontSize: '0.8125rem',
    color: 'var(--cyan)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  },
  conversationsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xs)',
    flex: 1,
    overflowY: 'auto',
  },
  conversationItem: {
    padding: 'var(--space-md)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  conversationAgent: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    marginBottom: 'var(--space-xs)',
  },
  agentDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  agentName: {
    fontSize: '0.75rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  conversationQuery: {
    fontSize: '0.875rem',
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-sm)',
    lineHeight: 1.4,
  },
  conversationMeta: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  conversationTime: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  healthCard: {
    gridColumn: '1',
    gridRow: '2',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
  },
  healthList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-md)',
  },
  healthItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
  },
  healthInfo: {
    width: '100px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  healthTeam: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  healthChange: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
    fontSize: '0.6875rem',
    fontWeight: 500,
  },
  healthBarContainer: {
    flex: 1,
    height: '8px',
    background: 'var(--elevated)',
    borderRadius: 'var(--radius-full)',
    overflow: 'hidden',
  },
  healthBar: {
    height: '100%',
    borderRadius: 'var(--radius-full)',
  },
  healthScore: {
    width: '40px',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    textAlign: 'right',
    fontFamily: 'var(--font-mono)',
  },
  actionsCard: {
    display: 'none', // Hidden in this layout, shown on smaller screens
  },
  actionsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 'var(--space-sm)',
    marginTop: 'var(--space-md)',
  },
  quickAction: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-md)',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontSize: '0.875rem',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
}
