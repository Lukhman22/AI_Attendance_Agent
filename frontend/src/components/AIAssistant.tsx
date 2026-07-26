import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot, ChevronDown, ChevronUp, Mic, Square, Volume2, VolumeX, Copy, Check, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import { aiApi } from '../services'
import { Card } from './ui'
import { clsx } from '../utils/format'

interface Message {
  id: string
  role: 'user' | 'ai'
  content: string
  references?: Record<string, any>
  isError?: boolean
  timestamp?: number
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  return (
    <button 
      onClick={handleCopy} 
      className="rounded-md p-1.5 text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-600 dark:hover:bg-ink-800 dark:hover:text-ink-300" 
      title="Copy message"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-brand-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-2 py-3">
      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500/60" style={{ animationDelay: '0ms' }} />
      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500/60" style={{ animationDelay: '150ms' }} />
      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500/60" style={{ animationDelay: '300ms' }} />
    </div>
  )
}

export function AIAssistant({ context: dashboardContext }: { context?: { work_date?: string; year?: number; month?: number } }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chatContext, setChatContext] = useState<Record<string, any>>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Voice states
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    setChatContext(prev => ({ ...prev, ...dashboardContext }))
  }, [dashboardContext])

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, isTranscribing])

  const formatTime = (ts?: number) => {
    if (!ts) return ''
    return new Date(ts).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  }

  const speakText = (text: string) => {
    if (isMuted || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }

  const stopSpeaking = () => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }

  const handleMicrophoneClick = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        setIsRecording(false)
        setIsTranscribing(true)
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        
        stream.getTracks().forEach(track => track.stop())
        mediaRecorderRef.current = null
        
        try {
          const { text } = await aiApi.transcribe(audioBlob)
          if (text) {
            await handleSend(text, true)
          }
        } catch (error) {
          toast.error("Failed to transcribe audio or model unavailable.")
        } finally {
          setIsTranscribing(false)
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      toast.error("Microphone permission denied.")
    }
  }

  const handleSend = async (question: string, isVoice: boolean = false) => {
    if (!question.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: Date.now(),
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const sendContext = { ...chatContext, input_source: isVoice ? 'Voice' : 'Typed' }
      // @ts-ignore - response typing may not have context yet
      const response = await aiApi.ask(question, sendContext)
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response.answer,
        references: response.references,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, aiMessage])
      // @ts-ignore
      if (response.context) setChatContext(response.context)
      if (isVoice) {
        speakText(response.answer)
      }
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: error?.response?.data?.detail || error?.message || "Sorry, I encountered an error while trying to process your request.",
        isError: true,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(input)
    }
  }

  return (
    <Card className="flex h-[700px] flex-col overflow-hidden border-0 bg-white shadow-xl ring-1 ring-ink-200/50 dark:bg-ink-950 dark:ring-ink-800/50">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-ink-100 bg-white px-6 py-4 dark:border-ink-800 dark:bg-ink-950">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">HR Intelligence</h2>
            <p className="text-xs font-medium text-ink-500">Always-on Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isSpeaking && (
            <button 
              onClick={stopSpeaking} 
              className="flex items-center gap-1.5 rounded-md bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-600 transition-colors hover:bg-rose-100 dark:bg-rose-900/30 dark:text-rose-400"
            >
              <Square className="h-3 w-3" fill="currentColor" /> Stop
            </button>
          )}
          <button 
            onClick={() => {
              setIsMuted(!isMuted)
              if (!isMuted) stopSpeaking()
            }}
            className="rounded-full p-2 text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-600 dark:hover:bg-ink-800 dark:hover:text-ink-200"
            title={isMuted ? "Unmute Voice" : "Mute Voice"}
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto bg-ink-50/30 px-4 py-6 dark:bg-ink-900/10 sm:px-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-lg shadow-brand-500/20">
              <Bot className="h-8 w-8" />
            </div>
            <h3 className="font-display text-xl font-semibold text-ink-900 dark:text-ink-50">How can I help you today?</h3>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-ink-500 dark:text-ink-400">
              Ask me about attendance anomalies, individual payroll records, or generate complex insights.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className={clsx('flex animate-slide-up', msg.role === 'user' ? 'justify-end' : 'justify-start group')}>
                {msg.role === 'user' ? (
                  <div className="flex max-w-[85%] flex-col items-end gap-1.5">
                    <div className="rounded-2xl rounded-tr-sm bg-brand-600 px-5 py-3.5 text-[15px] leading-relaxed text-white shadow-sm">
                      {msg.content}
                    </div>
                    <span className="pr-1 text-[11px] font-medium text-ink-400">{formatTime(msg.timestamp)}</span>
                  </div>
                ) : (
                  <div className="flex max-w-[92%] gap-4">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="flex min-w-0 flex-col gap-1.5">
                      <div className="flex items-center gap-2 px-1">
                        <span className="text-[13px] font-semibold text-ink-900 dark:text-ink-50">AI Assistant</span>
                        <span className="text-[11px] font-medium text-ink-400">{formatTime(msg.timestamp)}</span>
                      </div>
                      
                      <div className={clsx(
                        'rounded-2xl rounded-tl-sm px-5 py-4 text-[15px] leading-relaxed shadow-sm ring-1',
                        msg.isError 
                          ? 'bg-rose-50 text-rose-800 ring-rose-200 dark:bg-rose-950/50 dark:text-rose-200 dark:ring-rose-900/50'
                          : 'bg-white text-ink-800 ring-ink-200/60 dark:bg-ink-900/50 dark:text-ink-200 dark:ring-ink-800/60'
                      )}>
                        <pre className="whitespace-pre-wrap font-sans text-[15px]">{msg.content}</pre>
                        
                        {msg.references && Object.keys(msg.references).length > 0 && (
                          <div className="mt-4 border-t border-ink-100 pt-4 dark:border-ink-800">
                            <References references={msg.references} />
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 px-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <CopyButton text={msg.content} />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {(isLoading || isTranscribing) && (
              <div className="flex justify-start">
                <div className="flex max-w-[92%] gap-4">
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-ink-400 to-ink-500 text-white shadow-sm dark:from-ink-700 dark:to-ink-800">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-[13px] font-semibold text-ink-900 dark:text-ink-50">AI Assistant</span>
                    </div>
                    <div className="flex items-center rounded-2xl rounded-tl-sm bg-white px-4 py-2 ring-1 ring-ink-200/60 dark:bg-ink-900/50 dark:ring-ink-800/60">
                      {isTranscribing ? (
                        <span className="text-sm font-medium text-ink-500 px-2 py-1">Transcribing audio...</span>
                      ) : (
                        <TypingIndicator />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Invisible element to scroll to */}
            <div ref={messagesEndRef} className="h-px" />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="shrink-0 border-t border-ink-100 bg-white p-4 dark:border-ink-800 dark:bg-ink-950 sm:p-6">
        <div className="mx-auto max-w-3xl">
          <div className="relative flex items-end gap-2 rounded-2xl bg-ink-50 p-1.5 ring-1 ring-ink-200 transition-shadow focus-within:bg-white focus-within:ring-2 focus-within:ring-brand-500 dark:bg-ink-900/50 dark:ring-ink-800 dark:focus-within:bg-ink-900">
            <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? "Listening to your voice..." : "Message AI Assistant..."}
              disabled={isLoading || isRecording || isTranscribing}
              className="min-h-[44px] w-full border-0 bg-transparent px-4 py-2.5 text-[15px] text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-0 dark:text-ink-50 dark:placeholder:text-ink-600"
            />
            <div className="flex shrink-0 items-center gap-1.5 pr-1.5 pb-1.5">
              <button
                onClick={handleMicrophoneClick}
                disabled={isLoading || isTranscribing || !('mediaDevices' in navigator)}
                className={clsx(
                  'flex h-8 w-8 items-center justify-center rounded-xl transition-all',
                  isRecording 
                    ? 'animate-pulse bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400' 
                    : 'text-ink-400 hover:bg-ink-200 hover:text-ink-700 dark:hover:bg-ink-800 dark:hover:text-ink-200'
                )}
                title={isRecording ? "Stop Recording" : "Use Voice"}
              >
                {isRecording ? <Square className="h-4 w-4" fill="currentColor" /> : <Mic className="h-4 w-4" />}
              </button>
              <button 
                onClick={() => handleSend(input, false)}
                disabled={isLoading || isRecording || isTranscribing || !input.trim()}
                className={clsx(
                  'flex h-8 w-8 items-center justify-center rounded-xl transition-all',
                  input.trim() && !isLoading && !isRecording && !isTranscribing
                    ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
                    : 'bg-ink-200 text-ink-400 dark:bg-ink-800 dark:text-ink-600'
                )}
                title="Send Message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="mt-3 text-center">
            <p className="text-[11px] text-ink-400">AI can make mistakes. Verify important HR decisions.</p>
          </div>
        </div>
      </div>
    </Card>
  )
}

function References({ references }: { references: Record<string, any> }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="w-full">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 transition-colors hover:text-brand-700 dark:text-brand-500 dark:hover:text-brand-400"
      >
        {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        {isOpen ? 'Hide Data Sources' : 'View Data Sources'}
      </button>
      
      {isOpen && (
        <div className="mt-3 overflow-hidden rounded-xl border border-ink-200/60 bg-ink-50/50 animate-fade-in dark:border-ink-800/60 dark:bg-ink-900/30">
          <div className="max-h-[200px] overflow-y-auto p-3 text-[11px] font-mono leading-relaxed text-ink-700 dark:text-ink-300">
            {Object.entries(references).map(([key, value]) => (
              <div key={key} className="mb-2 last:mb-0">
                <span className="font-semibold text-ink-900 dark:text-ink-100">{key}:</span>{' '}
                <span>
                  {Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
