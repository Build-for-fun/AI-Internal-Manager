import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Key, ExternalLink, X, Sparkles, ArrowRight } from 'lucide-react'

interface ApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (apiKey: string) => void
}

export default function ApiKeyModal({ isOpen, onClose, onSubmit }: ApiKeyModalProps) {
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedKey = apiKey.trim()

    if (!trimmedKey) {
      setError('Please enter your API key')
      return
    }

    if (trimmedKey.length < 10) {
      setError('API key seems too short')
      return
    }

    setError('')
    onSubmit(trimmedKey)
  }

  const handleGetKey = () => {
    window.open('https://www.keywordsai.co', '_blank', 'noopener,noreferrer')
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          style={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            style={styles.modal}
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
          >
            <button style={styles.closeBtn} onClick={onClose}>
              <X size={20} />
            </button>

            <div style={styles.iconWrapper}>
              <div style={styles.iconBg}>
                <Key size={32} style={{ color: 'var(--cyan)' }} />
              </div>
              <div style={styles.iconGlow} />
            </div>

            <h2 style={styles.title}>Connect to Keywords AI</h2>

            <p style={styles.description}>
              To access the dashboard, you need a Keywords AI API key.
              This powers the AI agents and analytics features.
            </p>

            <motion.button
              style={styles.getKeyBtn}
              onClick={handleGetKey}
              whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(123, 97, 255, 0.4)' }}
              whileTap={{ scale: 0.98 }}
            >
              <Sparkles size={18} />
              Get Your Free API Key
              <ExternalLink size={16} />
            </motion.button>

            <div style={styles.divider}>
              <span style={styles.dividerLine} />
              <span style={styles.dividerText}>then paste it below</span>
              <span style={styles.dividerLine} />
            </div>

            <form onSubmit={handleSubmit} style={styles.form}>
              <div style={styles.inputWrapper}>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value)
                    setError('')
                  }}
                  style={styles.input}
                  autoFocus
                />
                {error && <span style={styles.error}>{error}</span>}
              </div>

              <motion.button
                type="submit"
                style={styles.submitBtn}
                whileHover={{ scale: 1.02, boxShadow: '0 0 40px rgba(0, 245, 212, 0.4)' }}
                whileTap={{ scale: 0.98 }}
              >
                Enter Dashboard
                <ArrowRight size={18} />
              </motion.button>
            </form>

            <p style={styles.footer}>
              Your API key is stored locally and never sent to our servers.
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.8)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    position: 'relative',
    width: '100%',
    maxWidth: '480px',
    background: 'linear-gradient(180deg, var(--surface) 0%, var(--abyss) 100%)',
    border: '1px solid var(--border)',
    borderRadius: '24px',
    padding: '48px 40px',
    textAlign: 'center',
  },
  closeBtn: {
    position: 'absolute',
    top: '16px',
    right: '16px',
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  iconWrapper: {
    position: 'relative',
    display: 'inline-flex',
    marginBottom: '24px',
  },
  iconBg: {
    width: '80px',
    height: '80px',
    borderRadius: '24px',
    background: 'linear-gradient(135deg, rgba(0, 245, 212, 0.15), rgba(123, 97, 255, 0.15))',
    border: '1px solid rgba(0, 245, 212, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconGlow: {
    position: 'absolute',
    inset: '-10px',
    borderRadius: '30px',
    background: 'radial-gradient(circle, rgba(0, 245, 212, 0.2) 0%, transparent 70%)',
    filter: 'blur(15px)',
    zIndex: -1,
  },
  title: {
    fontSize: '1.75rem',
    fontWeight: 700,
    marginBottom: '12px',
    letterSpacing: '-0.01em',
  },
  description: {
    fontSize: '1rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
    marginBottom: '32px',
  },
  getKeyBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 28px',
    background: 'linear-gradient(135deg, var(--violet), var(--violet-dim))',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    fontSize: '0.9375rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'var(--font-display)',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    margin: '32px 0',
  },
  dividerLine: {
    flex: 1,
    height: '1px',
    background: 'var(--border)',
  },
  dividerText: {
    fontSize: '0.8125rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  inputWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  input: {
    width: '100%',
    padding: '16px 20px',
    background: 'var(--void)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    color: 'var(--text-primary)',
    fontSize: '1rem',
    fontFamily: 'var(--font-mono)',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  error: {
    fontSize: '0.8125rem',
    color: 'var(--rose)',
    textAlign: 'left',
  },
  submitBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
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
  },
  footer: {
    marginTop: '24px',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
}
