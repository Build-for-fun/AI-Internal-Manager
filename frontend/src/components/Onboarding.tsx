import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle,
  Circle,
  Clock,
  ChevronRight,
  Play,
  Pause,
  Mic,
  BookOpen,
  Users,
  Code,
  Shield,
  Building,
  MessageSquare,
  Award,
  ArrowRight,
  Sparkles,
} from 'lucide-react'

interface OnboardingTask {
  id: string
  title: string
  description: string
  duration: string
  status: 'completed' | 'in_progress' | 'pending'
  category: string
}

interface OnboardingFlow {
  id: string
  role: string
  title: string
  description: string
  progress: number
  totalTasks: number
  completedTasks: number
  estimatedTime: string
  icon: typeof Code
}

const onboardingFlows: OnboardingFlow[] = [
  {
    id: '1',
    role: 'engineer',
    title: 'Software Engineer Onboarding',
    description: 'Technical setup, codebase overview, and development practices',
    progress: 68,
    totalTasks: 12,
    completedTasks: 8,
    estimatedTime: '4 hours remaining',
    icon: Code,
  },
  {
    id: '2',
    role: 'manager',
    title: 'Engineering Manager Path',
    description: 'Team processes, reporting, and management tools',
    progress: 0,
    totalTasks: 10,
    completedTasks: 0,
    estimatedTime: '6 hours total',
    icon: Users,
  },
  {
    id: '3',
    role: 'security',
    title: 'Security & Compliance',
    description: 'Security policies, compliance requirements, and best practices',
    progress: 100,
    totalTasks: 8,
    completedTasks: 8,
    estimatedTime: 'Completed',
    icon: Shield,
  },
]

const currentTasks: OnboardingTask[] = [
  {
    id: '1',
    title: 'Complete Development Environment Setup',
    description: 'Install required tools, configure IDE, and verify local build',
    duration: '30 min',
    status: 'completed',
    category: 'Technical Setup',
  },
  {
    id: '2',
    title: 'Review Authentication Service Architecture',
    description: 'Understand our JWT-based auth system and OAuth2 integration',
    duration: '45 min',
    status: 'completed',
    category: 'Codebase',
  },
  {
    id: '3',
    title: 'Complete API Design Guidelines Module',
    description: 'Learn our REST API standards and best practices',
    duration: '1 hour',
    status: 'in_progress',
    category: 'Standards',
  },
  {
    id: '4',
    title: 'Set Up CI/CD Pipeline Access',
    description: 'Get access to GitHub Actions and deployment workflows',
    duration: '20 min',
    status: 'pending',
    category: 'DevOps',
  },
  {
    id: '5',
    title: 'Join Team Slack Channels',
    description: 'Join #engineering, #platform-team, and #incident-response',
    duration: '10 min',
    status: 'pending',
    category: 'Communication',
  },
]

const achievements = [
  { id: 1, title: 'Quick Starter', description: 'Completed first module', icon: Sparkles, earned: true },
  { id: 2, title: 'Team Player', description: 'Joined all channels', icon: Users, earned: true },
  { id: 3, title: 'Code Explorer', description: 'Reviewed 5 services', icon: Code, earned: false },
  { id: 4, title: 'Security Pro', description: 'Completed security training', icon: Shield, earned: true },
]

export default function Onboarding() {
  const [selectedFlow, setSelectedFlow] = useState<OnboardingFlow>(onboardingFlows[0])
  const [voiceMode, setVoiceMode] = useState(false)
  const [expandedTask, setExpandedTask] = useState<string | null>(null)

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Onboarding Journey</h2>
          <p style={styles.subtitle}>
            Welcome! Complete your personalized onboarding to get up to speed
          </p>
        </div>
        <motion.button
          style={{
            ...styles.voiceBtn,
            ...(voiceMode ? styles.voiceBtnActive : {}),
          }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setVoiceMode(!voiceMode)}
        >
          <Mic size={18} />
          {voiceMode ? 'Voice Mode Active' : 'Start Voice Onboarding'}
          {voiceMode && <div style={styles.voicePulse} />}
        </motion.button>
      </div>

      <div style={styles.mainGrid}>
        {/* Left column - Progress and tasks */}
        <div style={styles.leftColumn}>
          {/* Current flow progress */}
          <motion.div
            style={styles.progressCard}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div style={styles.progressHeader}>
              <div style={styles.progressIcon}>
                <selectedFlow.icon size={24} />
              </div>
              <div style={styles.progressInfo}>
                <h3 style={styles.progressTitle}>{selectedFlow.title}</h3>
                <p style={styles.progressDesc}>{selectedFlow.description}</p>
              </div>
            </div>

            <div style={styles.progressStats}>
              <div style={styles.progressBarContainer}>
                <motion.div
                  style={styles.progressBar}
                  initial={{ width: 0 }}
                  animate={{ width: `${selectedFlow.progress}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                />
              </div>
              <div style={styles.progressMeta}>
                <span style={styles.progressPercent}>{selectedFlow.progress}%</span>
                <span style={styles.progressTasks}>
                  {selectedFlow.completedTasks}/{selectedFlow.totalTasks} tasks
                </span>
                <span style={styles.progressTime}>
                  <Clock size={12} />
                  {selectedFlow.estimatedTime}
                </span>
              </div>
            </div>
          </motion.div>

          {/* Tasks list */}
          <div style={styles.tasksCard}>
            <div style={styles.tasksHeader}>
              <h3 style={styles.tasksTitle}>Your Tasks</h3>
              <div style={styles.taskFilters}>
                <button style={{ ...styles.filterBtn, ...styles.filterBtnActive }}>All</button>
                <button style={styles.filterBtn}>Pending</button>
                <button style={styles.filterBtn}>Completed</button>
              </div>
            </div>

            <div style={styles.tasksList}>
              {currentTasks.map((task, index) => (
                <motion.div
                  key={task.id}
                  style={{
                    ...styles.taskItem,
                    ...(expandedTask === task.id ? styles.taskItemExpanded : {}),
                  }}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
                >
                  <div style={styles.taskMain}>
                    <div style={styles.taskStatus}>
                      {task.status === 'completed' ? (
                        <CheckCircle size={20} style={{ color: 'var(--emerald)' }} />
                      ) : task.status === 'in_progress' ? (
                        <div style={styles.inProgressIcon}>
                          <Circle size={20} style={{ color: 'var(--cyan)' }} />
                          <div style={styles.progressDot} />
                        </div>
                      ) : (
                        <Circle size={20} style={{ color: 'var(--text-dim)' }} />
                      )}
                    </div>
                    <div style={styles.taskContent}>
                      <div style={styles.taskHeader}>
                        <span style={styles.taskCategory}>{task.category}</span>
                        <span style={styles.taskDuration}>
                          <Clock size={12} />
                          {task.duration}
                        </span>
                      </div>
                      <h4
                        style={{
                          ...styles.taskTitle,
                          textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                          opacity: task.status === 'completed' ? 0.6 : 1,
                        }}
                      >
                        {task.title}
                      </h4>
                      <AnimatePresence>
                        {expandedTask === task.id && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            style={styles.taskExpanded}
                          >
                            <p style={styles.taskDescription}>{task.description}</p>
                            {task.status !== 'completed' && (
                              <motion.button
                                style={styles.startBtn}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                              >
                                {task.status === 'in_progress' ? (
                                  <>
                                    <Play size={14} />
                                    Continue
                                  </>
                                ) : (
                                  <>
                                    <ArrowRight size={14} />
                                    Start Task
                                  </>
                                )}
                              </motion.button>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                    <ChevronRight
                      size={16}
                      style={{
                        color: 'var(--text-dim)',
                        transform: expandedTask === task.id ? 'rotate(90deg)' : 'none',
                        transition: 'transform 0.2s',
                      }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column - Flows and achievements */}
        <div style={styles.rightColumn}>
          {/* Onboarding flows */}
          <div style={styles.flowsCard}>
            <h3 style={styles.sectionTitle}>Onboarding Paths</h3>
            <div style={styles.flowsList}>
              {onboardingFlows.map((flow) => (
                <motion.div
                  key={flow.id}
                  style={{
                    ...styles.flowItem,
                    borderColor: selectedFlow.id === flow.id ? 'var(--cyan)' : 'var(--border)',
                    background: selectedFlow.id === flow.id ? 'var(--cyan-glow)' : 'var(--abyss)',
                  }}
                  whileHover={{ borderColor: 'var(--border-glow)' }}
                  onClick={() => setSelectedFlow(flow)}
                >
                  <div
                    style={{
                      ...styles.flowIcon,
                      background:
                        flow.progress === 100
                          ? 'var(--emerald-glow)'
                          : flow.progress > 0
                          ? 'var(--cyan-glow)'
                          : 'var(--elevated)',
                      color:
                        flow.progress === 100
                          ? 'var(--emerald)'
                          : flow.progress > 0
                          ? 'var(--cyan)'
                          : 'var(--text-muted)',
                    }}
                  >
                    <flow.icon size={20} />
                  </div>
                  <div style={styles.flowContent}>
                    <span style={styles.flowTitle}>{flow.title}</span>
                    <div style={styles.flowProgress}>
                      <div style={styles.flowProgressBar}>
                        <div
                          style={{
                            ...styles.flowProgressFill,
                            width: `${flow.progress}%`,
                            background:
                              flow.progress === 100
                                ? 'var(--emerald)'
                                : 'var(--cyan)',
                          }}
                        />
                      </div>
                      <span style={styles.flowPercent}>{flow.progress}%</span>
                    </div>
                  </div>
                  {flow.progress === 100 && (
                    <CheckCircle size={16} style={{ color: 'var(--emerald)' }} />
                  )}
                </motion.div>
              ))}
            </div>
          </div>

          {/* Achievements */}
          <div style={styles.achievementsCard}>
            <h3 style={styles.sectionTitle}>Achievements</h3>
            <div style={styles.achievementsList}>
              {achievements.map((achievement) => (
                <motion.div
                  key={achievement.id}
                  style={{
                    ...styles.achievementItem,
                    opacity: achievement.earned ? 1 : 0.4,
                  }}
                  whileHover={achievement.earned ? { scale: 1.05 } : {}}
                >
                  <div
                    style={{
                      ...styles.achievementIcon,
                      background: achievement.earned
                        ? 'linear-gradient(135deg, var(--amber), var(--amber-glow))'
                        : 'var(--elevated)',
                    }}
                  >
                    <achievement.icon
                      size={20}
                      style={{
                        color: achievement.earned ? 'var(--void)' : 'var(--text-dim)',
                      }}
                    />
                  </div>
                  <div style={styles.achievementContent}>
                    <span style={styles.achievementTitle}>{achievement.title}</span>
                    <span style={styles.achievementDesc}>{achievement.description}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Quick help */}
          <motion.div
            style={styles.helpCard}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <div style={styles.helpIcon}>
              <MessageSquare size={24} />
            </div>
            <div style={styles.helpContent}>
              <h4 style={styles.helpTitle}>Need Help?</h4>
              <p style={styles.helpDesc}>
                Ask our AI assistant any questions about your onboarding
              </p>
            </div>
            <motion.button
              style={styles.helpBtn}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Start Chat
            </motion.button>
          </motion.div>
        </div>
      </div>
    </div>
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
  voiceBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-lg)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
    fontWeight: 500,
    cursor: 'pointer',
    position: 'relative',
    overflow: 'hidden',
  },
  voiceBtnActive: {
    background: 'var(--cyan-glow)',
    borderColor: 'var(--cyan)',
    color: 'var(--cyan)',
  },
  voicePulse: {
    position: 'absolute',
    inset: 0,
    background: 'var(--cyan)',
    opacity: 0.2,
    animation: 'pulse-glow 1.5s ease-in-out infinite',
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 360px',
    gap: 'var(--space-lg)',
  },
  leftColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
  },
  progressCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-xl)',
  },
  progressHeader: {
    display: 'flex',
    gap: 'var(--space-lg)',
    marginBottom: 'var(--space-xl)',
  },
  progressIcon: {
    width: '56px',
    height: '56px',
    borderRadius: 'var(--radius-lg)',
    background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--void)',
    flexShrink: 0,
  },
  progressInfo: {
    flex: 1,
  },
  progressTitle: {
    fontSize: '1.125rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-xs)',
  },
  progressDesc: {
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
  },
  progressStats: {},
  progressBarContainer: {
    height: '8px',
    background: 'var(--elevated)',
    borderRadius: 'var(--radius-full)',
    overflow: 'hidden',
    marginBottom: 'var(--space-md)',
  },
  progressBar: {
    height: '100%',
    background: 'linear-gradient(90deg, var(--cyan), var(--violet))',
    borderRadius: 'var(--radius-full)',
  },
  progressMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-lg)',
  },
  progressPercent: {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
  },
  progressTasks: {
    fontSize: '0.875rem',
    color: 'var(--text-secondary)',
  },
  progressTime: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    fontSize: '0.875rem',
    color: 'var(--text-muted)',
    marginLeft: 'auto',
  },
  tasksCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
    flex: 1,
  },
  tasksHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-lg)',
  },
  tasksTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  taskFilters: {
    display: 'flex',
    gap: 'var(--space-xs)',
  },
  filterBtn: {
    padding: 'var(--space-xs) var(--space-sm)',
    background: 'transparent',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    fontSize: '0.75rem',
    cursor: 'pointer',
  },
  filterBtnActive: {
    background: 'var(--elevated)',
    color: 'var(--text-primary)',
  },
  tasksList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  taskItem: {
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  taskItemExpanded: {
    borderColor: 'var(--border-glow)',
  },
  taskMain: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 'var(--space-md)',
  },
  taskStatus: {
    paddingTop: '2px',
  },
  inProgressIcon: {
    position: 'relative',
  },
  progressDot: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--cyan)',
    animation: 'pulse-glow 1.5s ease-in-out infinite',
  },
  taskContent: {
    flex: 1,
  },
  taskHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-xs)',
  },
  taskCategory: {
    fontSize: '0.6875rem',
    fontWeight: 500,
    color: 'var(--cyan)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  taskDuration: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '0.6875rem',
    color: 'var(--text-dim)',
  },
  taskTitle: {
    fontSize: '0.9375rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
    lineHeight: 1.4,
  },
  taskExpanded: {
    marginTop: 'var(--space-md)',
    overflow: 'hidden',
  },
  taskDescription: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
    lineHeight: 1.5,
    marginBottom: 'var(--space-md)',
  },
  startBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: 'var(--void)',
    fontSize: '0.8125rem',
    fontWeight: 500,
    cursor: 'pointer',
  },
  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
  },
  flowsCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
  },
  sectionTitle: {
    fontSize: '0.9375rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: 'var(--space-md)',
  },
  flowsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  flowItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  flowIcon: {
    width: '40px',
    height: '40px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  flowContent: {
    flex: 1,
    minWidth: 0,
  },
  flowTitle: {
    fontSize: '0.8125rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
    display: 'block',
    marginBottom: 'var(--space-xs)',
  },
  flowProgress: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  flowProgressBar: {
    flex: 1,
    height: '4px',
    background: 'var(--elevated)',
    borderRadius: 'var(--radius-full)',
    overflow: 'hidden',
  },
  flowProgressFill: {
    height: '100%',
    borderRadius: 'var(--radius-full)',
    transition: 'width 0.3s ease',
  },
  flowPercent: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    minWidth: '32px',
  },
  achievementsCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-lg)',
  },
  achievementsList: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 'var(--space-sm)',
  },
  achievementItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    textAlign: 'center',
    cursor: 'pointer',
  },
  achievementIcon: {
    width: '44px',
    height: '44px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  achievementContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  achievementTitle: {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  achievementDesc: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
  },
  helpCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    padding: 'var(--space-lg)',
    background: 'linear-gradient(135deg, var(--violet-glow), var(--cyan-glow))',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
  },
  helpIcon: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--surface)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--violet)',
    flexShrink: 0,
  },
  helpContent: {
    flex: 1,
  },
  helpTitle: {
    fontSize: '0.9375rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '2px',
  },
  helpDesc: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  helpBtn: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontSize: '0.8125rem',
    fontWeight: 500,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
}
