import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Users,
  GitPullRequest,
  Clock,
  AlertTriangle,
  CheckCircle,
  Activity,
  Calendar,
  ChevronDown,
  ArrowRight,
  Zap,
} from 'lucide-react'

const velocityData = [
  { sprint: 'S1', planned: 45, completed: 42 },
  { sprint: 'S2', planned: 50, completed: 48 },
  { sprint: 'S3', planned: 48, completed: 51 },
  { sprint: 'S4', planned: 52, completed: 49 },
  { sprint: 'S5', planned: 55, completed: 54 },
  { sprint: 'S6', planned: 53, completed: 56 },
]

const workloadData = [
  { name: 'Platform', value: 35, color: 'var(--cyan)' },
  { name: 'Backend', value: 28, color: 'var(--violet)' },
  { name: 'Frontend', value: 22, color: 'var(--amber)' },
  { name: 'DevOps', value: 15, color: 'var(--emerald)' },
]

const burndownData = [
  { day: 'Mon', ideal: 100, actual: 100 },
  { day: 'Tue', ideal: 83, actual: 92 },
  { day: 'Wed', ideal: 67, actual: 78 },
  { day: 'Thu', ideal: 50, actual: 62 },
  { day: 'Fri', ideal: 33, actual: 45 },
  { day: 'Sat', ideal: 17, actual: 28 },
  { day: 'Sun', ideal: 0, actual: 12 },
]

const bottlenecks = [
  {
    id: 1,
    type: 'Review Delay',
    description: 'PRs waiting >48h for review in Backend team',
    severity: 'high',
    affected: 5,
    trend: 'up',
  },
  {
    id: 2,
    type: 'Blocked Tasks',
    description: 'Tasks blocked by external dependencies',
    severity: 'medium',
    affected: 3,
    trend: 'stable',
  },
  {
    id: 3,
    type: 'Knowledge Silo',
    description: 'Auth service has single owner (bus factor = 1)',
    severity: 'high',
    affected: 1,
    trend: 'stable',
  },
]

const teamMembers = [
  { name: 'Sarah Chen', role: 'Lead', tasks: 8, completed: 6, avatar: 'SC' },
  { name: 'Mike Johnson', role: 'Senior', tasks: 12, completed: 10, avatar: 'MJ' },
  { name: 'Emily Davis', role: 'Senior', tasks: 10, completed: 9, avatar: 'ED' },
  { name: 'Alex Kim', role: 'Mid', tasks: 6, completed: 5, avatar: 'AK' },
  { name: 'Jordan Lee', role: 'Junior', tasks: 4, completed: 4, avatar: 'JL' },
]

const teams = ['All Teams', 'Platform', 'Backend', 'Frontend', 'DevOps']

export default function TeamAnalytics() {
  const [selectedTeam, setSelectedTeam] = useState('All Teams')
  const [timeRange, setTimeRange] = useState('This Sprint')

  return (
    <div style={styles.container}>
      {/* Header with filters */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Team Analytics</h2>
          <p style={styles.subtitle}>Monitor team health, velocity, and bottlenecks</p>
        </div>
        <div style={styles.filters}>
          <div style={styles.dropdown}>
            <Users size={16} />
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              style={styles.select}
            >
              {teams.map((team) => (
                <option key={team} value={team}>
                  {team}
                </option>
              ))}
            </select>
            <ChevronDown size={14} />
          </div>
          <div style={styles.dropdown}>
            <Calendar size={16} />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={styles.select}
            >
              <option>This Sprint</option>
              <option>Last 30 Days</option>
              <option>Last Quarter</option>
            </select>
            <ChevronDown size={14} />
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div style={styles.metricsGrid}>
        <MetricCard
          icon={Zap}
          label="Health Score"
          value="87"
          suffix="/100"
          change="+3%"
          trend="up"
          color="emerald"
        />
        <MetricCard
          icon={Activity}
          label="Avg Velocity"
          value="52"
          suffix="pts"
          change="+8%"
          trend="up"
          color="cyan"
        />
        <MetricCard
          icon={GitPullRequest}
          label="PR Cycle Time"
          value="18"
          suffix="hrs"
          change="-4hrs"
          trend="up"
          color="violet"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Bottlenecks"
          value="3"
          suffix="active"
          change="+1"
          trend="down"
          color="amber"
        />
      </div>

      {/* Charts grid */}
      <div style={styles.chartsGrid}>
        {/* Velocity chart */}
        <motion.div
          style={styles.chartCard}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Sprint Velocity</h3>
            <div style={styles.chartLegend}>
              <span style={styles.legendItem}>
                <span style={{ ...styles.legendDot, background: 'var(--cyan)' }} />
                Planned
              </span>
              <span style={styles.legendItem}>
                <span style={{ ...styles.legendDot, background: 'var(--violet)' }} />
                Completed
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={velocityData} barGap={4}>
              <XAxis
                dataKey="sprint"
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
                }}
              />
              <Bar dataKey="planned" fill="var(--cyan)" radius={[4, 4, 0, 0]} opacity={0.6} />
              <Bar dataKey="completed" fill="var(--violet)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Burndown chart */}
        <motion.div
          style={styles.chartCard}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Sprint Burndown</h3>
            <span className="badge amber">Behind Schedule</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={burndownData}>
              <XAxis
                dataKey="day"
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
                }}
              />
              <Line
                type="monotone"
                dataKey="ideal"
                stroke="var(--text-muted)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="var(--cyan)"
                strokeWidth={2}
                dot={{ fill: 'var(--cyan)', strokeWidth: 0, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Workload distribution */}
        <motion.div
          style={styles.chartCard}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Workload Distribution</h3>
          </div>
          <div style={styles.pieContainer}>
            <ResponsiveContainer width="50%" height={180}>
              <PieChart>
                <Pie
                  data={workloadData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {workloadData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div style={styles.pieLabels}>
              {workloadData.map((item) => (
                <div key={item.name} style={styles.pieLabel}>
                  <span style={{ ...styles.pieDot, background: item.color }} />
                  <span style={styles.pieName}>{item.name}</span>
                  <span style={styles.pieValue}>{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Bottlenecks */}
        <motion.div
          style={{ ...styles.chartCard, gridColumn: 'span 2' }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Active Bottlenecks</h3>
            <motion.button
              style={styles.viewAllBtn}
              whileHover={{ color: 'var(--text-primary)' }}
            >
              View all <ArrowRight size={14} />
            </motion.button>
          </div>
          <div style={styles.bottlenecksList}>
            {bottlenecks.map((item) => (
              <motion.div
                key={item.id}
                style={styles.bottleneckCard}
                whileHover={{ borderColor: 'var(--border-glow)' }}
              >
                <div
                  style={{
                    ...styles.severityIndicator,
                    background:
                      item.severity === 'high' ? 'var(--rose)' : 'var(--amber)',
                  }}
                />
                <div style={styles.bottleneckContent}>
                  <div style={styles.bottleneckHeader}>
                    <span style={styles.bottleneckType}>{item.type}</span>
                    <span
                      className={`badge ${item.severity === 'high' ? 'rose' : 'amber'}`}
                    >
                      {item.severity}
                    </span>
                  </div>
                  <p style={styles.bottleneckDesc}>{item.description}</p>
                  <div style={styles.bottleneckMeta}>
                    <span>{item.affected} affected</span>
                    <span
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        color:
                          item.trend === 'up'
                            ? 'var(--rose)'
                            : item.trend === 'down'
                            ? 'var(--emerald)'
                            : 'var(--text-muted)',
                      }}
                    >
                      {item.trend === 'up' ? (
                        <TrendingUp size={12} />
                      ) : item.trend === 'down' ? (
                        <TrendingDown size={12} />
                      ) : null}
                      {item.trend}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Team members */}
        <motion.div
          style={styles.chartCard}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Team Members</h3>
            <span style={styles.memberCount}>{teamMembers.length} members</span>
          </div>
          <div style={styles.membersList}>
            {teamMembers.map((member) => (
              <motion.div
                key={member.name}
                style={styles.memberCard}
                whileHover={{ background: 'var(--elevated)' }}
              >
                <div style={styles.memberAvatar}>{member.avatar}</div>
                <div style={styles.memberInfo}>
                  <span style={styles.memberName}>{member.name}</span>
                  <span style={styles.memberRole}>{member.role}</span>
                </div>
                <div style={styles.memberProgress}>
                  <div style={styles.progressBar}>
                    <motion.div
                      style={styles.progressFill}
                      initial={{ width: 0 }}
                      animate={{ width: `${(member.completed / member.tasks) * 100}%` }}
                      transition={{ duration: 0.8, delay: 0.2 }}
                    />
                  </div>
                  <span style={styles.progressText}>
                    {member.completed}/{member.tasks}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function MetricCard({
  icon: Icon,
  label,
  value,
  suffix,
  change,
  trend,
  color,
}: {
  icon: typeof Activity
  label: string
  value: string
  suffix: string
  change: string
  trend: 'up' | 'down'
  color: string
}) {
  const isPositive = trend === 'up'

  return (
    <motion.div
      style={styles.metricCard}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}
    >
      <div
        style={{
          ...styles.metricIcon,
          background: `var(--${color}-glow)`,
          color: `var(--${color})`,
        }}
      >
        <Icon size={20} />
      </div>
      <div style={styles.metricContent}>
        <span style={styles.metricLabel}>{label}</span>
        <div style={styles.metricValue}>
          <span>{value}</span>
          <span style={styles.metricSuffix}>{suffix}</span>
        </div>
      </div>
      <div
        style={{
          ...styles.metricChange,
          color: isPositive ? 'var(--emerald)' : 'var(--rose)',
        }}
      >
        {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
        {change}
      </div>
    </motion.div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xl)',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-xs)',
  },
  subtitle: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
  },
  filters: {
    display: 'flex',
    gap: 'var(--space-md)',
  },
  dropdown: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
  },
  select: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: '0.875rem',
    cursor: 'pointer',
    outline: 'none',
    appearance: 'none',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 'var(--space-lg)',
  },
  metricCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    padding: 'var(--space-lg)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    cursor: 'pointer',
    transition: 'all var(--transition-base)',
  },
  metricIcon: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricContent: {
    flex: 1,
  },
  metricLabel: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    display: 'block',
    marginBottom: '2px',
  },
  metricValue: {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
  },
  metricSuffix: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
    marginLeft: '4px',
  },
  metricChange: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
    fontSize: '0.75rem',
    fontWeight: 500,
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 'var(--space-lg)',
  },
  chartCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
  },
  chartHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-md)',
  },
  chartTitle: {
    fontSize: '0.9375rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  chartLegend: {
    display: 'flex',
    gap: 'var(--space-md)',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  pieContainer: {
    display: 'flex',
    alignItems: 'center',
  },
  pieLabels: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  pieLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  pieDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  pieName: {
    fontSize: '0.8125rem',
    color: 'var(--text-secondary)',
    minWidth: '70px',
  },
  pieValue: {
    fontSize: '0.8125rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
  },
  viewAllBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    fontSize: '0.75rem',
    cursor: 'pointer',
  },
  bottlenecksList: {
    display: 'flex',
    gap: 'var(--space-md)',
  },
  bottleneckCard: {
    flex: 1,
    display: 'flex',
    gap: 'var(--space-md)',
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  severityIndicator: {
    width: '4px',
    borderRadius: 'var(--radius-full)',
    flexShrink: 0,
  },
  bottleneckContent: {
    flex: 1,
  },
  bottleneckHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-xs)',
  },
  bottleneckType: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  bottleneckDesc: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    lineHeight: 1.4,
    marginBottom: 'var(--space-sm)',
  },
  bottleneckMeta: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '0.6875rem',
    color: 'var(--text-dim)',
  },
  memberCount: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  membersList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xs)',
  },
  memberCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    padding: 'var(--space-sm)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  memberAvatar: {
    width: '32px',
    height: '32px',
    borderRadius: 'var(--radius-md)',
    background: 'linear-gradient(135deg, var(--violet), var(--cyan))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.6875rem',
    fontWeight: 600,
    color: 'var(--void)',
  },
  memberInfo: {
    flex: 1,
  },
  memberName: {
    fontSize: '0.8125rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
    display: 'block',
  },
  memberRole: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
  },
  memberProgress: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  progressBar: {
    width: '60px',
    height: '4px',
    background: 'var(--elevated)',
    borderRadius: 'var(--radius-full)',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'var(--cyan)',
    borderRadius: 'var(--radius-full)',
  },
  progressText: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    minWidth: '35px',
  },
}
