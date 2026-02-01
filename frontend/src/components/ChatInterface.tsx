import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Mic,
  MicOff,
  Paperclip,
  MoreVertical,
  Bot,
  User,
  Sparkles,
  RefreshCw,
  Copy,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  Zap,
  BookOpen,
  Users,
  GraduationCap,
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  timestamp: Date
  sources?: { title: string; type: string }[]
}

interface ChatInterfaceProps {
  voiceActive: boolean
  setVoiceActive: (active: boolean) => void
}

const agentInfo = {
  orchestrator: { name: 'Orchestrator', color: 'var(--cyan)', icon: Zap },
  knowledge: { name: 'Knowledge Agent', color: 'var(--violet)', icon: BookOpen },
  team_analysis: { name: 'Team Analysis', color: 'var(--amber)', icon: Users },
  onboarding: { name: 'Onboarding Agent', color: 'var(--emerald)', icon: GraduationCap },
}

const initialMessages: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content:
      "Welcome to NEXUS Mission Control. I'm your AI assistant with access to your company's knowledge base, team analytics, and onboarding systems. How can I help you today?",
    agent: 'orchestrator',
    timestamp: new Date(Date.now() - 60000),
  },
]

const suggestedQueries = [
  'What are the Q4 OKRs for the engineering team?',
  'Show me the sprint velocity for Backend team',
  'Find documentation about the authentication service',
  'What is the onboarding checklist for new engineers?',
]

export default function ChatInterface({ voiceActive, setVoiceActive }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentAgent, setCurrentAgent] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Create conversation on mount
  useEffect(() => {
    const createConversation = async () => {
      try {
        const response = await fetch('/api/v1/chat/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: 'New Session',
            conversation_type: 'chat',
          }),
        })
        const data = await response.json()
        setConversationId(data.id)
      } catch (error) {
        console.error('Failed to create conversation:', error)
      }
    }
    createConversation()
  }, [])

  const handleSend = async () => {
    if (!input.trim() || !conversationId) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsTyping(true)
    setCurrentAgent('orchestrator')

    try {
      const response = await fetch(`/api/v1/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          stream: false,
        }),
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: data.message.id,
        role: 'assistant',
        content: data.message.content,
        agent: data.agent_used,
        timestamp: new Date(data.message.created_at),
        sources: data.sources,
      }

      setMessages((prev) => [...prev, assistantMessage])
      if (data.agent_used) setCurrentAgent(data.agent_used)
      
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error connecting to the server.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
      setTimeout(() => setCurrentAgent(null), 2000)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={styles.container}>
      {/* Chat header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.sessionInfo}>
            <h2 style={styles.sessionTitle}>New Conversation</h2>
            <span style={styles.sessionMeta}>Session started just now</span>
          </div>
        </div>
        <div style={styles.headerActions}>
          <motion.button
            style={styles.headerBtn}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <RefreshCw size={16} />
            <span>New Chat</span>
          </motion.button>
          <motion.button
            style={styles.headerIconBtn}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <MoreVertical size={18} />
          </motion.button>
        </div>
      </div>

      {/* Messages area */}
      <div style={styles.messagesContainer}>
        <div style={styles.messagesList}>
          <AnimatePresence>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          <AnimatePresence>
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                style={styles.typingIndicator}
              >
                {currentAgent && (
                  <div style={styles.routingBadge}>
                    <Sparkles size={12} />
                    <span>Routing to {agentInfo[currentAgent as keyof typeof agentInfo]?.name}</span>
                  </div>
                )}
                <div style={styles.typingDots}>
                  <span style={{ ...styles.typingDot, animationDelay: '0ms' }} />
                  <span style={{ ...styles.typingDot, animationDelay: '150ms' }} />
                  <span style={{ ...styles.typingDot, animationDelay: '300ms' }} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Suggested queries (show when few messages) */}
          {messages.length <= 1 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              style={styles.suggestionsContainer}
            >
              <span style={styles.suggestionsLabel}>Try asking:</span>
              <div style={styles.suggestionsList}>
                {suggestedQueries.map((query, i) => (
                  <motion.button
                    key={i}
                    style={styles.suggestionBtn}
                    whileHover={{ scale: 1.02, borderColor: 'var(--cyan)' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setInput(query)}
                  >
                    <Sparkles size={14} style={{ color: 'var(--cyan)' }} />
                    {query}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div style={styles.inputContainer}>
        <div style={styles.inputWrapper}>
          <motion.button
            style={styles.inputIconBtn}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <Paperclip size={18} />
          </motion.button>

          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your organization..."
            style={styles.textarea}
            rows={1}
          />

          <motion.button
            style={{
              ...styles.inputIconBtn,
              ...(voiceActive ? styles.voiceActive : {}),
            }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setVoiceActive(!voiceActive)}
          >
            {voiceActive ? <Mic size={18} /> : <MicOff size={18} />}
            {voiceActive && <div style={styles.voicePulseSmall} />}
          </motion.button>

          <motion.button
            style={{
              ...styles.sendBtn,
              opacity: input.trim() ? 1 : 0.5,
            }}
            whileHover={input.trim() ? { scale: 1.05 } : {}}
            whileTap={input.trim() ? { scale: 0.95 } : {}}
            onClick={handleSend}
            disabled={!input.trim()}
          >
            <Send size={18} />
          </motion.button>
        </div>

        <div style={styles.inputFooter}>
          <span style={styles.inputHint}>
            Press <kbd style={styles.kbd}>Enter</kbd> to send, <kbd style={styles.kbd}>Shift+Enter</kbd> for new line
          </span>
          <div style={styles.agentStatus}>
            <div className="status-dot processing" />
            <span>4 agents ready</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const agent = message.agent ? agentInfo[message.agent as keyof typeof agentInfo] : null
  const AgentIcon = agent?.icon || Bot

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        ...styles.messageWrapper,
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {!isUser && (
        <div
          style={{
            ...styles.avatar,
            background: agent?.color || 'var(--elevated)',
          }}
        >
          <AgentIcon size={18} style={{ color: 'var(--void)' }} />
        </div>
      )}

      <div
        style={{
          ...styles.messageBubble,
          ...(isUser ? styles.userMessage : styles.assistantMessage),
        }}
      >
        {!isUser && agent && (
          <div style={styles.agentLabel}>
            <span style={{ color: agent.color }}>{agent.name}</span>
          </div>
        )}

        <div style={styles.messageContent}>{message.content}</div>

        {message.sources && message.sources.length > 0 && (
          <div style={styles.sourcesContainer}>
            <span style={styles.sourcesLabel}>Sources:</span>
            {message.sources.map((source, i) => (
              <span key={i} className="badge" style={{ fontSize: '0.6875rem' }}>
                {source.title}
              </span>
            ))}
          </div>
        )}

        {!isUser && (
          <div style={styles.messageActions}>
            <motion.button
              style={styles.actionBtn}
              whileHover={{ color: 'var(--text-primary)' }}
            >
              <Copy size={14} />
            </motion.button>
            <motion.button
              style={styles.actionBtn}
              whileHover={{ color: 'var(--emerald)' }}
            >
              <ThumbsUp size={14} />
            </motion.button>
            <motion.button
              style={styles.actionBtn}
              whileHover={{ color: 'var(--rose)' }}
            >
              <ThumbsDown size={14} />
            </motion.button>
          </div>
        )}

        <span style={styles.timestamp}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {isUser && (
        <div style={{ ...styles.avatar, background: 'linear-gradient(135deg, var(--violet), var(--cyan))' }}>
          <User size={18} style={{ color: 'var(--void)' }} />
        </div>
      )}
    </motion.div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 64px - 48px)',
    background: 'var(--abyss)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-md) var(--space-lg)',
    borderBottom: '1px solid var(--border)',
    background: 'var(--surface)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
  },
  sessionInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  sessionTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  sessionMeta: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  headerBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    fontSize: '0.8125rem',
    cursor: 'pointer',
  },
  headerIconBtn: {
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  },
  messagesContainer: {
    flex: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  messagesList: {
    height: '100%',
    overflowY: 'auto',
    padding: 'var(--space-lg)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
  },
  messageWrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 'var(--space-md)',
  },
  avatar: {
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  messageBubble: {
    maxWidth: '70%',
    padding: 'var(--space-md) var(--space-lg)',
    borderRadius: 'var(--radius-lg)',
    position: 'relative',
  },
  userMessage: {
    background: 'linear-gradient(135deg, var(--violet), var(--violet-dim))',
    color: 'var(--text-primary)',
    borderBottomRightRadius: 'var(--radius-sm)',
  },
  assistantMessage: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    borderBottomLeftRadius: 'var(--radius-sm)',
  },
  agentLabel: {
    fontSize: '0.6875rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 'var(--space-sm)',
  },
  messageContent: {
    fontSize: '0.9375rem',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
  },
  sourcesContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    marginTop: 'var(--space-md)',
    paddingTop: 'var(--space-md)',
    borderTop: '1px solid var(--border)',
  },
  sourcesLabel: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  messageActions: {
    display: 'flex',
    gap: 'var(--space-xs)',
    marginTop: 'var(--space-sm)',
  },
  actionBtn: {
    padding: 'var(--space-xs)',
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    borderRadius: 'var(--radius-sm)',
  },
  timestamp: {
    position: 'absolute',
    bottom: '-20px',
    right: 0,
    fontSize: '0.6875rem',
    color: 'var(--text-dim)',
  },
  typingIndicator: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
    alignItems: 'flex-start',
    paddingLeft: '52px',
  },
  routingBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    padding: 'var(--space-xs) var(--space-sm)',
    background: 'var(--cyan-glow)',
    border: '1px solid rgba(0, 245, 212, 0.3)',
    borderRadius: 'var(--radius-full)',
    fontSize: '0.6875rem',
    color: 'var(--cyan)',
  },
  typingDots: {
    display: 'flex',
    gap: '4px',
    padding: 'var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
  },
  typingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--text-muted)',
    animation: 'pulse-glow 1s ease-in-out infinite',
  },
  suggestionsContainer: {
    marginTop: 'var(--space-xl)',
    paddingLeft: '52px',
  },
  suggestionsLabel: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    marginBottom: 'var(--space-md)',
    display: 'block',
  },
  suggestionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  suggestionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
    textAlign: 'left',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  inputContainer: {
    padding: 'var(--space-lg)',
    borderTop: '1px solid var(--border)',
    background: 'var(--surface)',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
  },
  inputIconBtn: {
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    borderRadius: 'var(--radius-md)',
    position: 'relative',
  },
  voiceActive: {
    color: 'var(--cyan)',
  },
  voicePulseSmall: {
    position: 'absolute',
    inset: '-2px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--cyan)',
    opacity: 0.5,
    animation: 'pulse-glow 1.5s ease-in-out infinite',
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    resize: 'none',
    color: 'var(--text-primary)',
    fontSize: '0.9375rem',
    lineHeight: 1.5,
    padding: 'var(--space-sm) 0',
    fontFamily: 'var(--font-display)',
  },
  sendBtn: {
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: 'var(--void)',
    cursor: 'pointer',
  },
  inputFooter: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 'var(--space-sm)',
    paddingLeft: 'var(--space-sm)',
  },
  inputHint: {
    fontSize: '0.6875rem',
    color: 'var(--text-dim)',
  },
  kbd: {
    padding: '2px 6px',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.625rem',
  },
  agentStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
  },
}
