import { motion } from 'framer-motion'
import {
  Activity,
  Users,
  BookOpen,
  MessageSquare,
  TrendingUp,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { useRbac } from '../contexts/RbacContext'

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

const okrItems = [
  {
    title: 'Reduce API latency by 30%',
    owner: 'Platform Org',
    status: 'On track',
  },
  {
    title: 'Ship unified design system',
    owner: 'Frontend Guild',
    status: 'At risk',
  },
  {
    title: 'Improve on-call MTTR to < 20m',
    owner: 'SRE',
    status: 'On track',
  },
]

const bottleneckItems = [
  {
    title: 'Code review queue spikes',
    impact: 'High',
    owner: 'Backend',
  },
  {
    title: 'QA regression backlog',
    impact: 'Medium',
    owner: 'Platform',
  },
]

const ownershipItems = [
  { area: 'Auth Service', owner: 'Identity Team' },
  { area: 'Billing APIs', owner: 'Payments Team' },
  { area: 'Incident Triage', owner: 'SRE' },
]

const velocityItems = [
  { sprint: 'Sprint 42', completed: 48, target: 50 },
  { sprint: 'Sprint 43', completed: 52, target: 50 },
  { sprint: 'Sprint 44', completed: 46, target: 50 },
]

const workloadItems = [
  { member: 'Sarah Chen', load: 'High', focus: 'Auth migration' },
  { member: 'Mike Johnson', load: 'Medium', focus: 'API gateway' },
  { member: 'Emily Davis', load: 'Balanced', focus: 'Frontend revamp' },
]

const memberStatus = [
  { name: 'Alex Kim', status: 'On track', focus: 'Refactor roadmap' },
  { name: 'Jordan Lee', status: 'Needs support', focus: 'Testing backlog' },
]

const personalTasks = [
  { task: 'Finish PR review', due: 'Today' },
  { task: 'Update ADR for caching', due: 'Tomorrow' },
  { task: 'Prepare sprint demo', due: 'Fri' },
]

const knowledgeLinks = [
  { title: 'Team architecture map', type: 'Diagram' },
  { title: 'API onboarding guide', type: 'Doc' },
  { title: 'Runbooks index', type: 'Index' },
]

const onboardingSteps = [
  { step: 'Complete security training', status: 'In progress' },
  { step: 'Meet your buddy', status: 'Scheduled' },
  { step: 'Submit equipment checklist', status: 'Done' },
]

const helpResources = [
  { title: 'IT Helpdesk', channel: '#it-help' },
  { title: 'Engineering Handbook', channel: 'wiki/handbook' },
  { title: 'People Ops', channel: '#people-ops' },
]

const teamIntroduction = [
  { name: 'Priya Rao', role: 'Team Lead' },
  { name: 'Dylan Park', role: 'Onboarding Buddy' },
]

const executiveSummary = [
  'Customer satisfaction remains above 95% with stable response times.',
  'Platform roadmap is on track with two cross-team dependencies.',
  'Hiring plan ahead of Q2 with 6 open roles in Engineering.',
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

const widgetMeta: Record<string, { title: string; subtitle: string }> = {
  company_overview: {
    title: 'Company Overview',
    subtitle: 'Key company-wide operational metrics',
  },
  department_overview: {
    title: 'Department Overview',
    subtitle: 'Department-level performance snapshot',
  },
  team_overview: {
    title: 'Team Overview',
    subtitle: 'Team-level health and velocity signals',
  },
  personal_tasks: {
    title: 'My Tasks',
    subtitle: 'Your current priorities',
  },
  all_teams_health: {
    title: 'All Teams Health',
    subtitle: 'Cross-team health indicators',
  },
  team_health: {
    title: 'Team Health',
    subtitle: 'Recent health deltas across teams',
  },
  cross_team_analytics: {
    title: 'Cross-Team Analytics',
    subtitle: 'Organization-wide activity overview',
  },
  department_analytics: {
    title: 'Department Analytics',
    subtitle: 'Activity trends within your department',
  },
  team_analytics: {
    title: 'Team Analytics',
    subtitle: 'Team activity and throughput signals',
  },
  my_analytics: {
    title: 'My Analytics',
    subtitle: 'Your personal performance insights',
  },
  team_activity: {
    title: 'Team Activity',
    subtitle: 'Recent discussions and actions',
  },
  company_okrs: {
    title: 'Company OKRs',
    subtitle: 'Top-level objectives and progress',
  },
  department_okrs: {
    title: 'Department OKRs',
    subtitle: 'Department objectives and progress',
  },
  executive_summary: {
    title: 'Executive Summary',
    subtitle: 'Leadership highlights for the week',
  },
  bottleneck_analysis: {
    title: 'Bottleneck Analysis',
    subtitle: 'Company-wide delivery risks',
  },
  team_bottlenecks: {
    title: 'Team Bottlenecks',
    subtitle: 'Delivery risks within your teams',
  },
  ownership_map: {
    title: 'Ownership Map',
    subtitle: 'Critical service ownership coverage',
  },
  ownership_lookup: {
    title: 'Ownership Lookup',
    subtitle: 'Key contacts for shared systems',
  },
  sprint_velocity: {
    title: 'Sprint Velocity',
    subtitle: 'Recent sprint delivery performance',
  },
  team_workload: {
    title: 'Team Workload',
    subtitle: 'Workload distribution for your team',
  },
  member_status: {
    title: 'Member Status',
    subtitle: 'Team member focus and health',
  },
  team_knowledge: {
    title: 'Team Knowledge',
    subtitle: 'Quick links to team documentation',
  },
  onboarding_progress: {
    title: 'Onboarding Progress',
    subtitle: 'Your onboarding checklist',
  },
  next_steps: {
    title: 'Next Steps',
    subtitle: 'Recommended onboarding actions',
  },
  team_introduction: {
    title: 'Team Introduction',
    subtitle: 'Key people to meet',
  },
  help_resources: {
    title: 'Help Resources',
    subtitle: 'Support channels and references',
  },
}

export default function Dashboard() {
  const { dashboard, loading } = useRbac()
  const widgets = dashboard?.widgets ?? []
  const scopeLevel = dashboard?.data_scope?.level

  if (loading) {
    return <div style={{ color: 'var(--text-secondary)' }}>Loading dashboard…</div>
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={styles.container}
    >
      <div style={styles.dashboardHeader}>
        <div>
          <h2 style={styles.dashboardTitle}>Dashboard</h2>
          <p style={styles.dashboardSubtitle}>Your RBAC-scoped operational view</p>
        </div>
        {scopeLevel && (
          <span className="badge cyan" style={styles.scopeBadge}>
            Scope: {String(scopeLevel).toUpperCase()}
          </span>
        )}
      </div>

      {widgets.length === 0 ? (
        <div style={styles.emptyState}>No dashboard widgets assigned.</div>
      ) : (
        <div style={styles.widgetsGrid}>
          {widgets.map((widgetId) => (
            <WidgetCard
              key={widgetId}
              title={widgetMeta[widgetId]?.title || 'Widget'}
              subtitle={widgetMeta[widgetId]?.subtitle || 'Role-based module'}
            >
              {renderWidgetContent(widgetId)}
            </WidgetCard>
          ))}
        </div>
      )}
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

function WidgetCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <motion.div variants={itemVariants} style={styles.widgetCard}>
      <div style={styles.widgetHeader}>
        <div>
          <h3 style={styles.cardTitle}>{title}</h3>
          <p style={styles.cardSubtitle}>{subtitle}</p>
        </div>
      </div>
      <div style={styles.widgetBody}>{children}</div>
    </motion.div>
  )
}

function renderWidgetContent(widgetId: string) {
  switch (widgetId) {
    case 'company_overview':
    case 'department_overview':
    case 'team_overview':
      return (
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
      )
    case 'all_teams_health':
    case 'team_health':
      return (
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
      )
    case 'cross_team_analytics':
    case 'department_analytics':
    case 'team_analytics':
    case 'my_analytics':
      return <ActivityChart />
    case 'team_activity':
      return (
        <div style={styles.widgetList}>
          {recentConversations.map((conv) => (
            <div key={conv.id} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{conv.query}</span>
                <span style={styles.widgetBadge}>{conv.status}</span>
              </div>
              <div style={styles.widgetListMeta}>{conv.agent} • {conv.time}</div>
            </div>
          ))}
        </div>
      )
    case 'company_okrs':
    case 'department_okrs':
      return (
        <div style={styles.widgetList}>
          {okrItems.map((okr) => (
            <div key={okr.title} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{okr.title}</span>
                <span style={styles.widgetBadge}>{okr.status}</span>
              </div>
              <div style={styles.widgetListMeta}>{okr.owner}</div>
            </div>
          ))}
        </div>
      )
    case 'executive_summary':
      return (
        <div style={styles.summaryList}>
          {executiveSummary.map((item) => (
            <div key={item} style={styles.summaryItem}>
              <span style={styles.summaryBullet} />
              <span>{item}</span>
            </div>
          ))}
        </div>
      )
    case 'bottleneck_analysis':
    case 'team_bottlenecks':
      return (
        <div style={styles.widgetList}>
          {bottleneckItems.map((item) => (
            <div key={item.title} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.title}</span>
                <span style={styles.widgetBadge}>{item.impact}</span>
              </div>
              <div style={styles.widgetListMeta}>{item.owner}</div>
            </div>
          ))}
        </div>
      )
    case 'ownership_map':
    case 'ownership_lookup':
      return (
        <div style={styles.widgetList}>
          {ownershipItems.map((item) => (
            <div key={item.area} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.area}</span>
                <span style={styles.widgetBadge}>{item.owner}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'sprint_velocity':
      return (
        <div style={styles.widgetList}>
          {velocityItems.map((item) => (
            <div key={item.sprint} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.sprint}</span>
                <span style={styles.widgetBadge}>
                  {item.completed}/{item.target}
                </span>
              </div>
              <div style={styles.widgetListMeta}>Completed story points</div>
            </div>
          ))}
        </div>
      )
    case 'team_workload':
      return (
        <div style={styles.widgetList}>
          {workloadItems.map((item) => (
            <div key={item.member} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.member}</span>
                <span style={styles.widgetBadge}>{item.load}</span>
              </div>
              <div style={styles.widgetListMeta}>{item.focus}</div>
            </div>
          ))}
        </div>
      )
    case 'member_status':
      return (
        <div style={styles.widgetList}>
          {memberStatus.map((item) => (
            <div key={item.name} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.name}</span>
                <span style={styles.widgetBadge}>{item.status}</span>
              </div>
              <div style={styles.widgetListMeta}>{item.focus}</div>
            </div>
          ))}
        </div>
      )
    case 'personal_tasks':
      return (
        <div style={styles.widgetList}>
          {personalTasks.map((item) => (
            <div key={item.task} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.task}</span>
                <span style={styles.widgetBadge}>{item.due}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'team_knowledge':
      return (
        <div style={styles.widgetList}>
          {knowledgeLinks.map((item) => (
            <div key={item.title} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.title}</span>
                <span style={styles.widgetBadge}>{item.type}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'onboarding_progress':
      return (
        <div style={styles.widgetList}>
          {onboardingSteps.map((item) => (
            <div key={item.step} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.step}</span>
                <span style={styles.widgetBadge}>{item.status}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'next_steps':
      return (
        <div style={styles.widgetList}>
          {onboardingSteps.map((item) => (
            <div key={item.step} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.step}</span>
                <span style={styles.widgetBadge}>{item.status}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'team_introduction':
      return (
        <div style={styles.widgetList}>
          {teamIntroduction.map((item) => (
            <div key={item.name} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.name}</span>
                <span style={styles.widgetBadge}>{item.role}</span>
              </div>
            </div>
          ))}
        </div>
      )
    case 'help_resources':
      return (
        <div style={styles.widgetList}>
          {helpResources.map((item) => (
            <div key={item.title} style={styles.widgetListItem}>
              <div style={styles.widgetListRow}>
                <span style={styles.widgetListTitle}>{item.title}</span>
                <span style={styles.widgetBadge}>{item.channel}</span>
              </div>
            </div>
          ))}
        </div>
      )
    default:
      return (
        <div style={styles.emptyState}>No data available for this widget.</div>
      )
  }
}

function ActivityChart() {
  return (
    <div style={styles.chartContainer}>
      <ResponsiveContainer width="100%" height={220}>
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
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xl)',
  },
  dashboardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  dashboardTitle: {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginBottom: 'var(--space-xs)',
  },
  dashboardSubtitle: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
  },
  scopeBadge: {
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  widgetsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: 'var(--space-lg)',
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
  widgetCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-md)',
  },
  widgetHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  widgetBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-md)',
  },
  widgetList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  widgetListItem: {
    padding: 'var(--space-sm)',
    borderRadius: 'var(--radius-md)',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
  },
  widgetListRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 'var(--space-sm)',
  },
  widgetListTitle: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  widgetListMeta: {
    marginTop: '2px',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  widgetBadge: {
    fontSize: '0.6875rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  summaryList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  summaryItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 'var(--space-sm)',
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
  },
  summaryBullet: {
    width: '8px',
    height: '8px',
    marginTop: '6px',
    borderRadius: '50%',
    background: 'var(--cyan)',
    flexShrink: 0,
  },
  emptyState: {
    color: 'var(--text-muted)',
    fontSize: '0.875rem',
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
