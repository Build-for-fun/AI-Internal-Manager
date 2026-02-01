import { useState, useRef, useCallback, useEffect } from 'react'

// Constants
const AUDIO_ANALYZER_FFT_SIZE = 256
const SAMPLE_RATE = 16000
const BIT_DEPTH = 16
const MAX_MESSAGES = 100
const MAX_RECONNECT_ATTEMPTS = 5

interface VoiceSource {
  title: string
  source?: string
  source_url?: string
}

interface VoiceMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  audioUrl?: string
  sources?: VoiceSource[]
  timestamp: Date
}

interface UseVoiceOptions {
  conversationId: string | null
  onTranscription?: (text: string) => void
  onResponse?: (text: string, sources?: VoiceSource[]) => void
  onError?: (error: string) => void
}

interface UseVoiceReturn {
  isConnected: boolean
  isConnecting: boolean
  isRecording: boolean
  isProcessing: boolean
  isSpeaking: boolean
  messages: VoiceMessage[]
  startRecording: () => Promise<void>
  stopRecording: () => void
  sendText: (text: string) => void
  stopSpeaking: () => void
  connect: () => Promise<void>
  disconnect: () => void
  audioLevel: number
}

export function useVoice({
  conversationId,
  onTranscription,
  onResponse,
  onError,
}: UseVoiceOptions): UseVoiceReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [messages, setMessages] = useState<VoiceMessage[]>([])
  const [audioLevel, setAudioLevel] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(null)

  // Refs for mutable values
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isRecordingRef = useRef(false)  // Fix: Use ref for recording state in animation loop
  const sessionIdRef = useRef<string | null>(null)  // Fix: Use ref for session ID in cleanup
  const reconnectAttemptsRef = useRef(0)
  const audioUrlsRef = useRef<Set<string>>(new Set())  // Fix: Track object URLs for cleanup
  const pendingAudioChunksRef = useRef<string[]>([])  // Accumulate audio chunks for streaming

  // Keep refs in sync with state
  useEffect(() => {
    isRecordingRef.current = isRecording
  }, [isRecording])

  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  // Clean up object URLs when messages change
  useEffect(() => {
    return () => {
      // Revoke all tracked object URLs on unmount
      audioUrlsRef.current.forEach(url => {
        URL.revokeObjectURL(url)
      })
      audioUrlsRef.current.clear()
    }
  }, [])

  // Get supported MIME type for MediaRecorder (cross-browser compatibility)
  const getSupportedMimeType = useCallback((): string => {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ]
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }
    return ''  // Use browser default
  }, [])

  // Play audio response
  const playAudio = useCallback((audioUrl: string) => {
    // Clean up previous audio
    if (currentAudioRef.current) {
      currentAudioRef.current.onended = null
      currentAudioRef.current.onerror = null
      currentAudioRef.current.pause()
    }

    const audio = new Audio(audioUrl)
    currentAudioRef.current = audio

    audio.onplay = () => setIsSpeaking(true)
    audio.onended = () => {
      setIsSpeaking(false)
      // Clean up object URL
      URL.revokeObjectURL(audioUrl)
      audioUrlsRef.current.delete(audioUrl)
    }
    audio.onerror = () => {
      setIsSpeaking(false)
      URL.revokeObjectURL(audioUrl)
      audioUrlsRef.current.delete(audioUrl)
      console.error('Audio playback error')
    }

    audio.play().catch(error => {
      console.error('Failed to play audio:', error)
      setIsSpeaking(false)
    })
  }, [])

  // Connect to ElevenLabs Conversational AI via backend bridge
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setIsConnecting(true)
    reconnectAttemptsRef.current = 0

    try {
      // Connect directly to ElevenLabs ConvAI WebSocket bridge
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/voice/agent/convai/ws`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Voice WebSocket connecting to ElevenLabs...')
      }

      ws.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data)

          switch (message.type) {
            case 'connected': {
              // Connected to ElevenLabs agent
              setIsConnected(true)
              setIsConnecting(false)
              setSessionId(message.agent_id || 'convai')
              reconnectAttemptsRef.current = 0
              console.log('Connected to ElevenLabs ConvAI agent:', message.agent_id)
              break
            }

            case 'session_started': {
              console.log('ElevenLabs conversation started:', message.conversation_id)
              break
            }

            case 'audio': {
              // Audio chunk from ElevenLabs agent - play immediately
              const audioData = message.data
              if (typeof audioData !== 'string' || !audioData) break

              // For ConvAI, audio chunks are playable PCM/MP3 segments
              pendingAudioChunksRef.current.push(audioData)

              // Start playing if not already speaking
              if (!isSpeaking && pendingAudioChunksRef.current.length === 1) {
                setIsSpeaking(true)
                playNextAudioChunk()
              }
              break
            }

            case 'transcript': {
              // Transcript from user or agent
              const role = message.role as 'user' | 'agent'
              const text = String(message.text || '')

              if (!text) break

              const voiceMsg: VoiceMessage = {
                id: Date.now().toString(),
                type: role === 'user' ? 'user' : 'assistant',
                text: text,
                timestamp: new Date(),
              }

              setMessages(prev => {
                const updated = [...prev, voiceMsg]
                return updated.slice(-MAX_MESSAGES)
              })

              if (role === 'user') {
                onTranscription?.(text)
                setIsProcessing(true)
              } else {
                onResponse?.(text)
                setIsProcessing(false)
              }
              break
            }

            case 'interruption': {
              // User interrupted the agent
              console.log('Agent interrupted by user')
              stopSpeakingInternal()
              break
            }

            case 'error': {
              console.error('ElevenLabs error:', message.message)
              onError?.(message.message || 'Voice agent error')
              break
            }

            case 'pong':
              break

            default:
              console.log('Unknown message type:', message.type, message)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('Voice WebSocket error:', error)
        setIsConnecting(false)
      }

      ws.onclose = () => {
        setIsConnected(false)
        setIsConnecting(false)
        setIsSpeaking(false)
        console.log('Voice WebSocket disconnected')

        // Attempt reconnection with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000
          reconnectAttemptsRef.current++
          console.log(`Attempting reconnection in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)
          setTimeout(() => {
            connect()
          }, delay)
        } else {
          onError?.('Connection lost. Please try reconnecting.')
        }
      }

    } catch (error) {
      console.error('Failed to connect voice:', error)
      setIsConnecting(false)
      onError?.(error instanceof Error ? error.message : 'Failed to connect')
    }
  }, [onTranscription, onResponse, onError, isSpeaking])

  // Play queued audio chunks sequentially
  const playNextAudioChunk = useCallback(() => {
    if (pendingAudioChunksRef.current.length === 0) {
      setIsSpeaking(false)
      return
    }

    const audioData = pendingAudioChunksRef.current.shift()
    if (!audioData) {
      setIsSpeaking(false)
      return
    }

    try {
      const audioBlob = base64ToBlob(audioData, 'audio/mpeg')
      const audioUrl = URL.createObjectURL(audioBlob)
      audioUrlsRef.current.add(audioUrl)

      const audio = new Audio(audioUrl)
      currentAudioRef.current = audio

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl)
        audioUrlsRef.current.delete(audioUrl)
        // Play next chunk if available
        playNextAudioChunk()
      }

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl)
        audioUrlsRef.current.delete(audioUrl)
        console.error('Audio chunk playback error')
        playNextAudioChunk()
      }

      audio.play().catch(error => {
        console.error('Failed to play audio chunk:', error)
        playNextAudioChunk()
      })
    } catch (error) {
      console.error('Error creating audio from chunk:', error)
      playNextAudioChunk()
    }
  }, [])

  // Internal stop speaking (clears queue)
  const stopSpeakingInternal = useCallback(() => {
    pendingAudioChunksRef.current = []
    if (currentAudioRef.current) {
      currentAudioRef.current.onended = null
      currentAudioRef.current.onerror = null
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    setIsSpeaking(false)
  }, [])

  // Disconnect from voice session
  const disconnect = useCallback(() => {
    // Reset reconnection attempts
    reconnectAttemptsRef.current = MAX_RECONNECT_ATTEMPTS  // Prevent auto-reconnect

    // Stop recording if active
    if (mediaRecorderRef.current && isRecordingRef.current) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      isRecordingRef.current = false
    }

    // Stop audio playback and clear queue
    pendingAudioChunksRef.current = []
    if (currentAudioRef.current) {
      currentAudioRef.current.onended = null
      currentAudioRef.current.onerror = null
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }

    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.onclose = null  // Prevent reconnection attempt
      wsRef.current.close()
      wsRef.current = null
    }

    // Revoke all tracked object URLs
    audioUrlsRef.current.forEach(url => {
      URL.revokeObjectURL(url)
    })
    audioUrlsRef.current.clear()

    setIsConnected(false)
    setIsConnecting(false)
    setSessionId(null)
    setAudioLevel(0)
    setIsSpeaking(false)
    setIsProcessing(false)
  }, [])

  // Store disconnect in ref for cleanup effect
  const disconnectRef = useRef(disconnect)
  useEffect(() => {
    disconnectRef.current = disconnect
  }, [disconnect])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnectRef.current()
    }
  }, [])

  // Start recording audio and stream to ElevenLabs in real-time
  const startRecording = useCallback(async () => {
    if (!isConnected) {
      await connect()
      // Wait a bit for connection to establish
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: SAMPLE_RATE,
        }
      })
      streamRef.current = stream

      // Set up audio analysis for level visualization
      audioContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE })
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = AUDIO_ANALYZER_FFT_SIZE
      source.connect(analyserRef.current)

      // Also create a ScriptProcessor to capture raw audio for streaming
      const scriptProcessor = audioContextRef.current.createScriptProcessor(4096, 1, 1)
      source.connect(scriptProcessor)
      scriptProcessor.connect(audioContextRef.current.destination)

      // Stream audio chunks in real-time to ElevenLabs
      scriptProcessor.onaudioprocess = (event) => {
        if (!isRecordingRef.current || wsRef.current?.readyState !== WebSocket.OPEN) return

        const inputData = event.inputBuffer.getChannelData(0)

        // Convert float32 to int16 PCM
        const pcmData = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputData[i]))
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        }

        // Convert to base64 and send
        const base64Audio = arrayBufferToBase64(pcmData.buffer)
        wsRef.current.send(JSON.stringify({
          type: 'audio',
          data: base64Audio,
        }))
      }

      // Start level monitoring (use ref to avoid stale closure)
      const updateLevel = () => {
        if (analyserRef.current && isRecordingRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
          analyserRef.current.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length
          setAudioLevel(average / 255)
          animationFrameRef.current = requestAnimationFrame(updateLevel)
        }
      }

      // Start recording state
      setIsRecording(true)
      isRecordingRef.current = true
      updateLevel()

    } catch (error) {
      console.error('Failed to start recording:', error)
      if (error instanceof Error && error.name === 'NotAllowedError') {
        onError?.('Microphone permission denied')
      } else {
        onError?.('Failed to access microphone')
      }
    }
  }, [isConnected, connect, onError])

  // Stop recording
  const stopRecording = useCallback(() => {
    setIsRecording(false)
    isRecordingRef.current = false

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    // Close audio context (stops the ScriptProcessor)
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }

    setAudioLevel(0)
  }, [])

  // Send text message (for typing while in voice mode)
  const sendText = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      setIsProcessing(true)

      // Add user message
      const userMsg: VoiceMessage = {
        id: Date.now().toString(),
        type: 'user',
        text: text,
        timestamp: new Date(),
      }
      setMessages(prev => {
        const updated = [...prev, userMsg]
        return updated.slice(-MAX_MESSAGES)
      })

      wsRef.current.send(JSON.stringify({
        type: 'text',
        query: text,  // Voice agent expects 'query' field
      }))
    }
  }, [])

  // Stop audio playback
  const stopSpeaking = useCallback(() => {
    if (currentAudioRef.current) {
      const audioUrl = currentAudioRef.current.src
      currentAudioRef.current.onended = null
      currentAudioRef.current.onerror = null
      currentAudioRef.current.pause()
      currentAudioRef.current = null
      setIsSpeaking(false)
      // Don't revoke URL here as it may still be referenced in messages
    }
  }, [])

  return {
    isConnected,
    isConnecting,
    isRecording,
    isProcessing,
    isSpeaking,
    messages,
    startRecording,
    stopRecording,
    sendText,
    stopSpeaking,
    connect,
    disconnect,
    audioLevel,
  }
}

// Helper functions

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const byteCharacters = atob(base64)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: mimeType })
}

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const result = reader.result as string
      // Remove data URL prefix safely
      const commaIndex = result.indexOf(',')
      const base64 = commaIndex >= 0 ? result.slice(commaIndex + 1) : result
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

async function convertToWav(audioBlob: Blob): Promise<Blob> {
  // Use AudioContext to decode and re-encode as WAV
  const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })

  try {
    const arrayBuffer = await audioBlob.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
    const wavBuffer = audioBufferToWav(audioBuffer)
    await audioContext.close()
    return new Blob([wavBuffer], { type: 'audio/wav' })
  } catch (error) {
    await audioContext.close()
    // Throw error instead of silent fallback - backend needs WAV format
    throw new Error('Audio conversion failed')
  }
}

function audioBufferToWav(buffer: AudioBuffer): ArrayBuffer {
  const numChannels = 1 // Mono
  const sampleRate = buffer.sampleRate
  const format = 1 // PCM

  const bytesPerSample = BIT_DEPTH / 8
  const blockAlign = numChannels * bytesPerSample
  const dataSize = buffer.length * blockAlign
  const bufferSize = 44 + dataSize

  const arrayBuffer = new ArrayBuffer(bufferSize)
  const view = new DataView(arrayBuffer)

  // WAV header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // Subchunk1Size
  view.setUint16(20, format, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true) // ByteRate
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, BIT_DEPTH, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  // Audio data (convert to mono and 16-bit)
  const channelData = buffer.getChannelData(0)
  let offset = 44
  for (let i = 0; i < channelData.length; i++) {
    const sample = Math.max(-1, Math.min(1, channelData[i]))
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
    offset += 2
  }

  return arrayBuffer
}

function writeString(view: DataView, offset: number, string: string): void {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i))
  }
}

export default useVoice
