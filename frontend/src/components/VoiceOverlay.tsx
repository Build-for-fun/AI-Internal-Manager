import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Volume2, Loader2, X, Phone, PhoneOff, MessageCircle } from 'lucide-react'

interface VoiceMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: Date
}

interface VoiceOverlayProps {
  isConnected: boolean
  isConnecting: boolean
  isListening: boolean
  isSpeaking: boolean
  messages: VoiceMessage[]
  onDisconnect: () => void
}

export default function VoiceOverlay({
  isConnected,
  isConnecting,
  isListening,
  isSpeaking,
  messages,
  onDisconnect,
}: VoiceOverlayProps) {
  // Don't render if not connected and not connecting
  if (!isConnected && !isConnecting) return null

  // Get the last few messages for display
  const recentMessages = messages.slice(-4)
  const lastUserMsg = [...messages].reverse().find(m => m.type === 'user')
  const lastAssistantMsg = [...messages].reverse().find(m => m.type === 'assistant')

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={styles.backdrop}
        onClick={(e) => {
          if (e.target === e.currentTarget) onDisconnect()
        }}
      >
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.8, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          style={styles.modal}
        >
          {/* Header */}
          <div style={styles.header}>
            <div style={styles.headerTitle}>
              <Phone size={20} style={{ color: 'var(--emerald)' }} />
              <span>Voice Assistant</span>
              {isConnected && (
                <span style={styles.connectedBadge}>Live</span>
              )}
            </div>
            <motion.button
              style={styles.closeBtn}
              whileHover={{ scale: 1.1, background: 'rgba(255, 82, 82, 0.2)' }}
              whileTap={{ scale: 0.9 }}
              onClick={onDisconnect}
              aria-label="End voice session"
            >
              <X size={24} />
            </motion.button>
          </div>

          {/* Main Content */}
          <div style={styles.content}>
            {/* Status Message */}
            <div style={styles.statusArea}>
              {isConnecting && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={styles.statusMessage}
                >
                  <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Connecting to voice assistant...</span>
                </motion.div>
              )}
              {isConnected && !isListening && !isSpeaking && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={styles.statusMessage}
                >
                  <MessageCircle size={24} style={{ color: 'var(--cyan)' }} />
                  <span>Start speaking anytime...</span>
                </motion.div>
              )}
              {isListening && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ ...styles.statusMessage, color: 'var(--emerald)' }}
                >
                  <Mic size={24} />
                  <span>Listening...</span>
                </motion.div>
              )}
              {isSpeaking && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ ...styles.statusMessage, color: 'var(--cyan)' }}
                >
                  <Volume2 size={24} />
                  <span>Speaking...</span>
                </motion.div>
              )}
            </div>

            {/* Visual Indicator */}
            <div style={styles.micArea}>
              <motion.div
                style={{
                  ...styles.bigMicIndicator,
                  background: isSpeaking
                    ? 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))'
                    : isListening
                    ? 'linear-gradient(135deg, var(--emerald), #059669)'
                    : 'linear-gradient(135deg, var(--violet), var(--violet-dim))',
                  boxShadow: isSpeaking
                    ? '0 0 60px rgba(0, 245, 212, 0.5)'
                    : isListening
                    ? '0 0 60px rgba(16, 185, 129, 0.5)'
                    : '0 0 40px rgba(139, 92, 246, 0.3)',
                }}
                animate={{
                  scale: isListening || isSpeaking ? [1, 1.05, 1] : 1,
                }}
                transition={{
                  duration: 1,
                  repeat: isListening || isSpeaking ? Infinity : 0,
                  ease: 'easeInOut',
                }}
              >
                {isSpeaking ? (
                  <Volume2 size={48} />
                ) : (
                  <Mic size={48} />
                )}

                {/* Pulse rings when active */}
                {(isListening || isSpeaking) && (
                  <>
                    <motion.div
                      style={{
                        ...styles.pulseRing,
                        borderColor: isSpeaking ? 'var(--cyan)' : 'var(--emerald)',
                      }}
                      animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                    <motion.div
                      style={{
                        ...styles.pulseRing,
                        borderColor: isSpeaking ? 'var(--cyan)' : 'var(--emerald)',
                      }}
                      animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity, delay: 0.5 }}
                    />
                  </>
                )}
              </motion.div>

              <span style={styles.micHint}>
                {isConnecting
                  ? 'Setting up...'
                  : isSpeaking
                  ? 'Agent is responding'
                  : 'Speak naturally - I\'m listening'}
              </span>
            </div>

            {/* Conversation History */}
            {(lastUserMsg || lastAssistantMsg) && (
              <div style={styles.conversation}>
                {lastUserMsg && (
                  <motion.div
                    key={lastUserMsg.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    style={styles.userBubble}
                  >
                    <span style={styles.bubbleLabel}>You</span>
                    <p style={styles.bubbleText}>{lastUserMsg.text}</p>
                  </motion.div>
                )}
                {lastAssistantMsg && (
                  <motion.div
                    key={lastAssistantMsg.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    style={styles.assistantBubble}
                  >
                    <span style={styles.bubbleLabel}>Assistant</span>
                    <p style={styles.bubbleText}>{lastAssistantMsg.text}</p>
                  </motion.div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div style={styles.footer}>
            <span style={styles.footerText}>
              Powered by ElevenLabs Conversational AI
            </span>
            <motion.button
              style={styles.endCallBtn}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onDisconnect}
            >
              <PhoneOff size={18} />
              <span>End Session</span>
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(5, 5, 10, 0.9)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
  },
  modal: {
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-xl)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-lg) var(--space-xl)',
    borderBottom: '1px solid var(--border)',
    background: 'var(--elevated)',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    fontSize: '1.125rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  connectedBadge: {
    padding: '4px 12px',
    background: 'var(--emerald-glow)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    borderRadius: 'var(--radius-full)',
    fontSize: '0.75rem',
    color: 'var(--emerald)',
    fontWeight: 500,
  },
  closeBtn: {
    width: '44px',
    height: '44px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flex: 1,
    padding: 'var(--space-xl)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-xl)',
    overflowY: 'auto',
  },
  statusArea: {
    textAlign: 'center',
    minHeight: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusMessage: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    fontSize: '1.25rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  micArea: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-lg)',
  },
  bigMicIndicator: {
    width: '140px',
    height: '140px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--void)',
    position: 'relative',
    transition: 'box-shadow 0.3s ease',
  },
  pulseRing: {
    position: 'absolute',
    inset: 0,
    borderRadius: '50%',
    border: '3px solid var(--emerald)',
    pointerEvents: 'none',
  },
  micHint: {
    fontSize: '1rem',
    color: 'var(--text-muted)',
    fontWeight: 500,
    textAlign: 'center',
  },
  conversation: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-md)',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '80%',
    padding: 'var(--space-md) var(--space-lg)',
    background: 'linear-gradient(135deg, var(--violet), var(--violet-dim))',
    borderRadius: 'var(--radius-lg)',
    borderBottomRightRadius: 'var(--radius-sm)',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    maxWidth: '80%',
    padding: 'var(--space-md) var(--space-lg)',
    background: 'var(--elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    borderBottomLeftRadius: 'var(--radius-sm)',
  },
  bubbleLabel: {
    display: 'block',
    fontSize: '0.6875rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: 'var(--text-muted)',
    marginBottom: '4px',
  },
  bubbleText: {
    fontSize: '0.9375rem',
    color: 'var(--text-primary)',
    lineHeight: 1.5,
    margin: 0,
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-md) var(--space-xl)',
    borderTop: '1px solid var(--border)',
    background: 'var(--abyss)',
  },
  footerText: {
    fontSize: '0.75rem',
    color: 'var(--text-dim)',
  },
  endCallBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-lg)',
    background: 'rgba(255, 82, 82, 0.1)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--rose)',
    fontSize: '0.875rem',
    fontWeight: 500,
    cursor: 'pointer',
  },
}
