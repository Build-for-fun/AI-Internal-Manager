import { useState, useRef, useCallback, useEffect } from 'react'
import { Conversation } from '@11labs/client'

// ElevenLabs Agent ID from user's configuration
const AGENT_ID = 'agent_4601kgc1063efqn8b3c4qea00sey'

interface VoiceMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: Date
}

interface UseElevenLabsVoiceOptions {
  onTranscription?: (text: string) => void
  onResponse?: (text: string) => void
  onError?: (error: string) => void
}

interface UseElevenLabsVoiceReturn {
  isConnected: boolean
  isConnecting: boolean
  isSpeaking: boolean
  isListening: boolean
  messages: VoiceMessage[]
  connect: () => Promise<void>
  disconnect: () => void
  status: 'disconnected' | 'connecting' | 'connected'
  mode: 'listening' | 'speaking' | 'idle'
}

export function useElevenLabsVoice({
  onTranscription,
  onResponse,
  onError,
}: UseElevenLabsVoiceOptions = {}): UseElevenLabsVoiceReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [messages, setMessages] = useState<VoiceMessage[]>([])
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [mode, setMode] = useState<'listening' | 'speaking' | 'idle'>('idle')

  const conversationRef = useRef<Conversation | null>(null)

  // Connect to ElevenLabs agent
  const connect = useCallback(async () => {
    if (conversationRef.current || isConnecting) {
      return
    }

    setIsConnecting(true)
    setStatus('connecting')

    try {
      // Request microphone permission first
      await navigator.mediaDevices.getUserMedia({ audio: true })

      // Start the conversation with ElevenLabs agent
      const conversation = await Conversation.startSession({
        agentId: AGENT_ID,
        onConnect: () => {
          console.log('Connected to ElevenLabs agent')
          setIsConnected(true)
          setIsConnecting(false)
          setStatus('connected')
        },
        onDisconnect: () => {
          console.log('Disconnected from ElevenLabs agent')
          setIsConnected(false)
          setIsConnecting(false)
          setStatus('disconnected')
          setIsSpeaking(false)
          setIsListening(false)
          setMode('idle')
          conversationRef.current = null
        },
        onMessage: (message) => {
          console.log('ElevenLabs message:', message)

          // Handle different message types
          if (message.type === 'user_transcript' || message.source === 'user') {
            const text = message.message || message.text || ''
            if (text && message.isFinal !== false) {
              const userMsg: VoiceMessage = {
                id: Date.now().toString(),
                type: 'user',
                text: text,
                timestamp: new Date(),
              }
              setMessages(prev => [...prev, userMsg].slice(-50))
              onTranscription?.(text)
            }
          } else if (message.type === 'agent_response' || message.source === 'ai') {
            const text = message.message || message.text || ''
            if (text) {
              const assistantMsg: VoiceMessage = {
                id: Date.now().toString(),
                type: 'assistant',
                text: text,
                timestamp: new Date(),
              }
              setMessages(prev => [...prev, assistantMsg].slice(-50))
              onResponse?.(text)
            }
          }
        },
        onError: (error) => {
          console.error('ElevenLabs error:', error)
          onError?.(error.message || 'Voice agent error')
          setIsConnecting(false)
          setStatus('disconnected')
        },
        onModeChange: (newMode) => {
          console.log('Mode changed:', newMode)
          setMode(newMode.mode || 'idle')
          setIsSpeaking(newMode.mode === 'speaking')
          setIsListening(newMode.mode === 'listening')
        },
        onStatusChange: (newStatus) => {
          console.log('Status changed:', newStatus)
          if (newStatus.status === 'connected') {
            setIsConnected(true)
            setIsConnecting(false)
            setStatus('connected')
          } else if (newStatus.status === 'connecting') {
            setIsConnecting(true)
            setStatus('connecting')
          } else {
            setIsConnected(false)
            setIsConnecting(false)
            setStatus('disconnected')
          }
        },
      })

      conversationRef.current = conversation

    } catch (error) {
      console.error('Failed to connect to ElevenLabs:', error)
      setIsConnecting(false)
      setStatus('disconnected')

      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          onError?.('Microphone permission denied. Please allow microphone access.')
        } else {
          onError?.(error.message || 'Failed to connect to voice agent')
        }
      } else {
        onError?.('Failed to connect to voice agent')
      }
    }
  }, [isConnecting, onTranscription, onResponse, onError])

  // Disconnect from ElevenLabs agent
  const disconnect = useCallback(async () => {
    if (conversationRef.current) {
      try {
        await conversationRef.current.endSession()
      } catch (error) {
        console.error('Error ending session:', error)
      }
      conversationRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
    setIsSpeaking(false)
    setIsListening(false)
    setStatus('disconnected')
    setMode('idle')
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (conversationRef.current) {
        conversationRef.current.endSession().catch(() => {})
      }
    }
  }, [])

  return {
    isConnected,
    isConnecting,
    isSpeaking,
    isListening,
    messages,
    connect,
    disconnect,
    status,
    mode,
  }
}

export default useElevenLabsVoice
