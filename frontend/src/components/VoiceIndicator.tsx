import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Volume2, Loader2, X, Phone, PhoneOff } from 'lucide-react'

interface VoiceIndicatorProps {
  isConnected: boolean
  isRecording: boolean
  isProcessing: boolean
  isSpeaking: boolean
  audioLevel: number
  onStopRecording: () => void
  onStopSpeaking: () => void
  onDisconnect: () => void
}

export default function VoiceIndicator({
  isConnected,
  isRecording,
  isProcessing,
  isSpeaking,
  audioLevel,
  onStopRecording,
  onStopSpeaking,
  onDisconnect,
}: VoiceIndicatorProps) {
  if (!isConnected && !isRecording && !isProcessing && !isSpeaking) {
    return null
  }

  const getStatus = () => {
    if (isRecording) return { text: 'Listening...', color: 'var(--rose)', icon: Mic }
    if (isProcessing) return { text: 'Processing...', color: 'var(--amber)', icon: Loader2 }
    if (isSpeaking) return { text: 'Speaking...', color: 'var(--cyan)', icon: Volume2 }
    if (isConnected) return { text: 'Voice Active', color: 'var(--emerald)', icon: Phone }
    return { text: 'Connecting...', color: 'var(--text-muted)', icon: Loader2 }
  }

  const status = getStatus()
  const StatusIcon = status.icon

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        style={styles.container}
      >
        <div style={styles.content}>
          {/* Audio visualization */}
          <div style={styles.visualizer}>
            {isRecording && (
              <AudioBars audioLevel={audioLevel} />
            )}
            {!isRecording && (
              <motion.div
                style={{
                  ...styles.iconWrapper,
                  background: status.color + '20',
                  borderColor: status.color,
                }}
                animate={isProcessing ? { rotate: 360 } : {}}
                transition={isProcessing ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}
              >
                <StatusIcon size={20} style={{ color: status.color }} />
              </motion.div>
            )}
          </div>

          {/* Status text */}
          <div style={styles.info}>
            <span style={{ ...styles.statusText, color: status.color }}>
              {status.text}
            </span>
            <span style={styles.hint}>
              {isRecording && 'Tap to stop recording'}
              {isSpeaking && 'Tap to stop playback'}
              {isConnected && !isRecording && !isProcessing && !isSpeaking && 'Tap mic to speak'}
            </span>
          </div>

          {/* Action buttons */}
          <div style={styles.actions}>
            {isRecording && (
              <motion.button
                style={{ ...styles.actionBtn, background: 'var(--rose)' }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onStopRecording}
                aria-label="Stop recording"
                title="Stop recording"
              >
                <X size={16} aria-hidden="true" />
              </motion.button>
            )}
            {isSpeaking && (
              <motion.button
                style={{ ...styles.actionBtn, background: 'var(--amber)' }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onStopSpeaking}
                aria-label="Stop playback"
                title="Stop playback"
              >
                <X size={16} aria-hidden="true" />
              </motion.button>
            )}
            {isConnected && (
              <motion.button
                style={{ ...styles.actionBtn, background: 'var(--rose)' }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onDisconnect}
                aria-label="End voice session"
                title="End voice session"
              >
                <PhoneOff size={16} aria-hidden="true" />
              </motion.button>
            )}
          </div>
        </div>

        {/* Pulse effect when recording */}
        {isRecording && (
          <motion.div
            style={styles.pulse}
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// Audio level bars visualization
function AudioBars({ audioLevel }: { audioLevel: number }) {
  const barCount = 5
  const bars = Array.from({ length: barCount }, (_, i) => {
    const threshold = (i + 1) / barCount
    const isActive = audioLevel >= threshold * 0.5
    const height = 8 + (audioLevel * 24 * (1 + i * 0.2))

    return (
      <motion.div
        key={i}
        style={{
          ...styles.bar,
          background: isActive ? 'var(--rose)' : 'var(--text-dim)',
        }}
        animate={{ height: isActive ? height : 8 }}
        transition={{ duration: 0.1 }}
      />
    )
  })

  return <div style={styles.bars}>{bars}</div>
}

// Floating voice overlay that shows during active voice session
export function VoiceOverlay({
  isConnected,
  isRecording,
  isProcessing,
  isSpeaking,
  audioLevel,
  transcript,
  response,
  onStartRecording,
  onStopRecording,
  onDisconnect,
}: {
  isConnected: boolean
  isRecording: boolean
  isProcessing: boolean
  isSpeaking: boolean
  audioLevel: number
  transcript?: string
  response?: string
  onStartRecording: () => void
  onStopRecording: () => void
  onDisconnect: () => void
}) {
  if (!isConnected) return null

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      style={styles.overlay}
    >
      <div style={styles.overlayHeader}>
        <div style={styles.overlayTitle}>
          <Phone size={16} style={{ color: 'var(--emerald)' }} />
          <span>Voice Mode</span>
        </div>
        <motion.button
          style={styles.closeBtn}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onDisconnect}
        >
          <X size={18} />
        </motion.button>
      </div>

      <div style={styles.overlayContent}>
        {/* Transcript */}
        {transcript && (
          <div style={styles.transcriptBox}>
            <span style={styles.transcriptLabel}>You said:</span>
            <p style={styles.transcriptText}>{transcript}</p>
          </div>
        )}

        {/* Response */}
        {response && (
          <div style={styles.responseBox}>
            <span style={styles.responseLabel}>Assistant:</span>
            <p style={styles.responseText}>{response}</p>
          </div>
        )}

        {/* Processing indicator */}
        {isProcessing && (
          <div style={styles.processingBox}>
            <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
            <span>Thinking...</span>
          </div>
        )}
      </div>

      {/* Main action button */}
      <div style={styles.overlayActions}>
        <motion.button
          style={{
            ...styles.mainMicBtn,
            background: isRecording
              ? 'linear-gradient(135deg, var(--rose), var(--rose-dim))'
              : 'linear-gradient(135deg, var(--cyan), var(--cyan-dim))',
          }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={isRecording ? onStopRecording : onStartRecording}
          disabled={isProcessing}
        >
          {isRecording ? (
            <>
              <AudioBars audioLevel={audioLevel} />
              <span>Tap to stop</span>
            </>
          ) : (
            <>
              <Mic size={24} />
              <span>Tap to speak</span>
            </>
          )}
        </motion.button>
      </div>

      {/* Speaking indicator */}
      {isSpeaking && (
        <motion.div
          style={styles.speakingIndicator}
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        >
          <Volume2 size={16} />
          <span>Speaking...</span>
        </motion.div>
      )}
    </motion.div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    marginBottom: 'var(--space-md)',
  },
  content: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
    flex: 1,
    zIndex: 1,
  },
  visualizer: {
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapper: {
    width: '40px',
    height: '40px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bars: {
    display: 'flex',
    alignItems: 'center',
    gap: '3px',
    height: '32px',
  },
  bar: {
    width: '4px',
    borderRadius: '2px',
    transition: 'height 0.1s ease',
  },
  info: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    flex: 1,
  },
  statusText: {
    fontSize: '0.875rem',
    fontWeight: 600,
  },
  hint: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  actions: {
    display: 'flex',
    gap: 'var(--space-sm)',
  },
  actionBtn: {
    width: '32px',
    height: '32px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--void)',
    cursor: 'pointer',
  },
  pulse: {
    position: 'absolute',
    inset: 0,
    borderRadius: 'var(--radius-lg)',
    border: '2px solid var(--rose)',
    pointerEvents: 'none',
  },
  // Overlay styles
  overlay: {
    position: 'fixed',
    bottom: '100px',
    right: '24px',
    width: '340px',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-xl)',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
    zIndex: 1000,
    overflow: 'hidden',
  },
  overlayHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-md) var(--space-lg)',
    borderBottom: '1px solid var(--border)',
    background: 'var(--elevated)',
  },
  overlayTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  closeBtn: {
    width: '28px',
    height: '28px',
    borderRadius: 'var(--radius-sm)',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  overlayContent: {
    padding: 'var(--space-md) var(--space-lg)',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  transcriptBox: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--violet-glow)',
    borderRadius: 'var(--radius-md)',
    marginBottom: 'var(--space-sm)',
  },
  transcriptLabel: {
    fontSize: '0.6875rem',
    color: 'var(--violet)',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  transcriptText: {
    fontSize: '0.875rem',
    color: 'var(--text-primary)',
    margin: 'var(--space-xs) 0 0',
    lineHeight: 1.4,
  },
  responseBox: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--cyan-glow)',
    borderRadius: 'var(--radius-md)',
    marginBottom: 'var(--space-sm)',
  },
  responseLabel: {
    fontSize: '0.6875rem',
    color: 'var(--cyan)',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  responseText: {
    fontSize: '0.875rem',
    color: 'var(--text-primary)',
    margin: 'var(--space-xs) 0 0',
    lineHeight: 1.4,
  },
  processingBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-md)',
    color: 'var(--text-muted)',
    fontSize: '0.875rem',
  },
  overlayActions: {
    padding: 'var(--space-lg)',
    display: 'flex',
    justifyContent: 'center',
    borderTop: '1px solid var(--border)',
    background: 'var(--abyss)',
  },
  mainMicBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-lg) var(--space-xl)',
    borderRadius: 'var(--radius-xl)',
    border: 'none',
    color: 'var(--void)',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    minWidth: '140px',
  },
  speakingIndicator: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm)',
    background: 'var(--cyan-glow)',
    color: 'var(--cyan)',
    fontSize: '0.75rem',
    fontWeight: 500,
  },
}
