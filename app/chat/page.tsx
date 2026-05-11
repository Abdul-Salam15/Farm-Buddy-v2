"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Send,
  Plus,
  MessageSquare,
  Sprout,
  Bug,
  Droplets,
  BookOpen,
  Cloud,
  Image as ImageIcon,
  Mic,
  User,
  Settings,
  LogOut,
  Menu,
  Leaf,
  Moon,
  Sun,
  Pause,
  Play,
  Copy,
  Check,
  X,
  Pencil,
  Trash2,
  Check as SaveIcon,
  ArrowDown,
  Search,
  MoreHorizontal,
  Loader2
} from "lucide-react"
import { useTheme } from "next-themes"
import { cn } from "@/lib/utils"
import { useTranslation } from "@/app/i18n/LanguageContext"
import { API_BASE_URL } from "@/lib/config"

interface Message {
  id: string | number
  role: "user" | "assistant"
  content: string
  image_url?: string
  references?: any[]
}

interface ConversationItem {
  id: number
  title: string
  updated_at: string
}

interface MessageSearchResult {
  conversation_id: number
  conversation_title: string
  snippet: string
  updated_at: string
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

function FormattedMessage({ content }: { content: string }) {
  // Split by [FARMBUDDY_REFS] to only show main content
  const mainContent = content.split('[FARMBUDDY_REFS]')[0].trim();

  // Basic markdown-like bold processing
  const parts = mainContent.split(/(\*\*.*?\*\*)/g);

  return (
    <div className="whitespace-pre-wrap break-words">
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="font-bold underline decoration-primary/30 underline-offset-2">{part.slice(2, -2)}</strong>;
        }
        return part;
      })}
    </div>
  );
}

export default function ChatPage() {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const { theme, setTheme } = useTheme()
  const [isSpeaking, setIsSpeaking] = useState<string | number | null>(null)
  const [isPaused, setIsPaused] = useState(false)
  const [isTTSLoading, setIsTTSLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<string | number | null>(null)
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [preferredLanguage, setPreferredLanguage] = useState("en")
  const audioPlayerKey = preferredLanguage;
  const [editingConvId, setEditingConvId] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [messageSearchResults, setMessageSearchResults] = useState<MessageSearchResult[]>([])
  const [isSearchingMessages, setIsSearchingMessages] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recognitionRef = useRef<any>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const ttsAbortRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const speechResultRef = useRef('')
  const audioContextRef = useRef<AudioContext | null>(null)
  const isAutoScrollingRef = useRef(true)
  const hasRestoredConvRef = useRef(false)

  const quickActions = [
    { icon: Leaf, label: t("chat.quick_actions.crop_disease") },
    { icon: Droplets, label: t("chat.quick_actions.irrigation") },
    { icon: Sun, label: t("chat.quick_actions.weather") },
    { icon: BookOpen, label: t("chat.quick_actions.best_practices") },
  ]

  const scrollToBottom = useCallback((force = false, smooth = false) => {
    if (force || isAutoScrollingRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" })
    }
  }, [])

  useEffect(() => {
    const scrollArea = scrollAreaRef.current
    if (!scrollArea) return

    const viewport = scrollArea.querySelector('[data-radix-scroll-area-viewport]')
    if (!viewport) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = viewport
      // If user is within 100px of bottom, enable auto-scroll
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
      isAutoScrollingRef.current = isAtBottom
      setShowScrollButton(!isAtBottom && scrollHeight > clientHeight)
    }

    viewport.addEventListener('scroll', handleScroll)
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Unlock Web Audio / HTML5 Audio on iOS PWA on first user interaction
  useEffect(() => {
    const unlock = () => {
      const AC = window.AudioContext || (window as any).webkitAudioContext
      if (!AC) return
      if (!audioContextRef.current) {
        audioContextRef.current = new AC()
      }
      if (audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume()
      }
    }
    document.addEventListener('click', unlock, { once: true })
    document.addEventListener('touchend', unlock, { once: true })
    return () => {
      document.removeEventListener('click', unlock)
      document.removeEventListener('touchend', unlock)
    }
  }, [])

  const API_BASE = `${API_BASE_URL}/chat`

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/list/`, { credentials: 'include' })
      const data = await res.json()
      if (data.success) {
        setConversations(data.conversations)
      }
    } catch (err) {
      console.error("Failed to fetch conversations", err)
    }
  }, [])

  const fetchUserProfile = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/profile/`, {
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      })
      const data = await res.json()
      if (data.success) {
        setPreferredLanguage(data.profile.preferred_language || "en")
        const username = data.profile.username
        const storedUser = localStorage.getItem('farmbuddy_user')
        if (storedUser && storedUser !== username) {
          localStorage.removeItem('farmbuddy_conv_id')
        }
        localStorage.setItem('farmbuddy_user', username)
      }
    } catch (err) {
      console.error("Failed to fetch user profile", err)
    }
  }, [])

  const [weatherData, setWeatherData] = useState<any>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)

  const handleMicClick = async () => {
    console.log("Mic button clicked, isRecording:", isRecording);
    if (isRecording) {
      // Stop MediaRecorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      // Stop SpeechRecognition
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      console.log("Recording stopped");
    } else {
      try {
        console.log("Requesting microphone access...");
        // 1. Setup MediaRecorder for robust backend transcription
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log("Microphone access granted, stream:", stream.active);

        // Detect best supported MIME type for this platform (iOS needs mp4, Chrome prefers webm)
        const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
        const supportedMime = preferredTypes.find(t => MediaRecorder.isTypeSupported(t)) ?? '';
        const mediaRecorder = supportedMime
          ? new MediaRecorder(stream, { mimeType: supportedMime })
          : new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];
        speechResultRef.current = '';

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          console.log("Recording stopped, chunks:", audioChunksRef.current.length);
          // Use the actual recorded MIME type (critical for iOS which uses audio/mp4)
          const actualMimeType = mediaRecorder.mimeType || 'audio/webm';
          const audioBlob = new Blob(audioChunksRef.current, { type: actualMimeType });
          stream.getTracks().forEach(track => track.stop());

          // If SpeechRecognition produced a final transcript, use it and skip backend
          if (speechResultRef.current.trim()) {
            console.log("Using SpeechRecognition result:", speechResultRef.current);
            speechResultRef.current = '';
            return;
          }
          speechResultRef.current = '';

          // No speech recognition result — send audio blob to backend for transcription
          console.log("Audio blob size:", audioBlob.size, "type:", actualMimeType);
          const ext = actualMimeType.includes('mp4') ? 'recording.mp4'
            : actualMimeType.includes('ogg') ? 'recording.ogg' : 'recording.webm';
          const formData = new FormData();
          formData.append('audio', audioBlob, ext);
          formData.append('language', preferredLanguage);

          setIsTranscribing(true);
          try {
            console.log("Sending to transcription API...");
            const res = await fetch(`${API_BASE}/api/transcribe/`, {
              method: 'POST',
              body: formData,
              credentials: 'include'
            });
            console.log("Transcription response status:", res.status);
            const data = await res.json();
            console.log("Transcription result:", data);
            if (data.success && data.text) {
              setInputValue(data.text);
            } else if (data.error) {
              console.error("Transcription error:", data.error);
              alert("Transcription failed: " + data.error);
            }
          } catch (err) {
            console.error("Failed to transcribe audio:", err);
            alert("Could not send audio for transcription.");
          } finally {
            setIsTranscribing(false);
          }
        };

        // 2. Setup SpeechRecognition for real-time visual feedback (best-effort)
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
          console.log("SpeechRecognition available, starting...");
          const recognition = new SpeechRecognition();
          recognitionRef.current = recognition;

          const langMap: Record<string, string> = {
            'en': 'en-US',
            'ha': 'ha-NG',
            'ig': 'ig-NG',
            'yo': 'yo-NG',
          };

          recognition.lang = langMap[preferredLanguage] || 'en-US';
          recognition.continuous = true;
          recognition.interimResults = true;

          recognition.onresult = (event: any) => {
            // Accumulate ALL final results from index 0 (not just from event.resultIndex)
            // so long multi-segment phrases aren't truncated
            let allFinal = '';
            let interim = '';
            for (let i = 0; i < event.results.length; i++) {
              if (event.results[i].isFinal) {
                allFinal += event.results[i][0].transcript;
              } else {
                interim += event.results[i][0].transcript;
              }
            }
            speechResultRef.current = allFinal;
            if (allFinal || interim) {
              console.log("Speech recognized:", { finalTranscript: allFinal, interimTranscript: interim });
              setInputValue(allFinal + interim);
            }
          };

          recognition.onerror = (event: any) => {
            console.warn("Speech recognition error:", event.error);
          };

          recognition.start();
        } else {
          console.log("SpeechRecognition not available on this browser");
        }

        mediaRecorder.start();
        setIsRecording(true);
        console.log("Recording started");
      } catch (err: any) {
        console.error("Microphone error:", err);
        let message = "Failed to start recording.";

        if (err.name === 'NotAllowedError') {
          message = "Microphone permission denied. Please enable it in browser settings.";
        } else if (err.name === 'NotFoundError') {
          message = "No microphone found on this device.";
        } else if (err.name === 'NotReadableError') {
          message = "Microphone is already in use by another app.";
        } else if (err.name === 'SecurityError') {
          message = "Microphone access blocked. Check browser/site permissions.";
        }

        console.log("Error details:", { name: err.name, message: err.message });
        alert(message);
      }
    }
  };

  const speakWithBrowser = (text: string) => {
    if (!window.speechSynthesis) {
      setIsSpeaking(null)
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    // Best-effort language mapping for browser TTS voices
    const langMap: Record<string, string> = { en: 'en-US', ha: 'ha', ig: 'ig', yo: 'yo' }
    utterance.lang = langMap[preferredLanguage] || 'en-US'
    utterance.onend = () => { setIsSpeaking(null); setIsPaused(false) }
    utterance.onerror = () => { setIsSpeaking(null); setIsPaused(false) }
    window.speechSynthesis.speak(utterance)
  }

  const playMessage = async (message: Message) => {
    // Clicking the same message while loading → cancel the request
    if (isSpeaking === message.id && isTTSLoading) {
      ttsAbortRef.current?.abort()
      ttsAbortRef.current = null
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
      setIsSpeaking(null); setIsPaused(false); setIsTTSLoading(false)
      return
    }

    // Clicking the same message while playing → pause / resume
    if (isSpeaking === message.id) {
      if (audioRef.current) {
        if (!isPaused) { audioRef.current.pause(); setIsPaused(true) }
        else { audioRef.current.play(); setIsPaused(false) }
      } else if (window.speechSynthesis) {
        if (!isPaused) { window.speechSynthesis.pause(); setIsPaused(true) }
        else { window.speechSynthesis.resume(); setIsPaused(false) }
      }
      return
    }

    // Cancel any in-flight request for a different message and stop its audio
    ttsAbortRef.current?.abort()
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }

    const abort = new AbortController()
    ttsAbortRef.current = abort

    setIsSpeaking(message.id)
    setIsPaused(false)
    setIsTTSLoading(true)

    const resetState = () => {
      setIsSpeaking(null); setIsPaused(false); setIsTTSLoading(false)
      audioRef.current = null
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/speak/`,
        {
          method: 'POST',
          credentials: 'include',
          signal: abort.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: message.content, language: preferredLanguage }),
        }
      )
      if (!response.ok) throw new Error(`TTS request failed: ${response.status}`)

      const contentType = response.headers.get('Content-Type') || 'audio/mpeg'

      // Stream via MediaSource so playback begins as soon as first chunks arrive
      if (response.body && typeof MediaSource !== 'undefined' && MediaSource.isTypeSupported(contentType)) {
        const ms = new MediaSource()
        const msUrl = URL.createObjectURL(ms)
        const audio = new Audio(msUrl)
        audioRef.current = audio

        audio.onended = () => { resetState(); URL.revokeObjectURL(msUrl) }

        ms.addEventListener('sourceopen', async () => {
          let sb: SourceBuffer
          try { sb = ms.addSourceBuffer(contentType) }
          catch {
            URL.revokeObjectURL(msUrl); audioRef.current = null
            const blob = await new Response(response.body).blob()
            const blobUrl = URL.createObjectURL(blob)
            const a = new Audio(blobUrl)
            audioRef.current = a
            a.onended = () => { resetState(); URL.revokeObjectURL(blobUrl) }
            setIsTTSLoading(false)
            await a.play().catch(() => { URL.revokeObjectURL(blobUrl); speakWithBrowser(message.content) })
            return
          }

          const reader = response.body!.getReader()
          const pump = async (): Promise<void> => {
            if (abort.signal.aborted) { reader.cancel(); return }
            const { done, value } = await reader.read()
            if (done) { if (ms.readyState === 'open') { try { ms.endOfStream() } catch {} } return }
            await new Promise<void>(r => { sb.addEventListener('updateend', () => r(), { once: true }); sb.appendBuffer(value) })
            return pump()
          }
          pump().catch(console.error)
        }, { once: true })

        // Begin playback as soon as browser has enough data buffered
        await new Promise<void>((resolve, reject) => {
          abort.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
          audio.addEventListener('canplay', async () => {
            setIsTTSLoading(false)
            try { await audio.play(); resolve() }
            catch (e) { URL.revokeObjectURL(msUrl); audioRef.current = null; reject(e) }
          }, { once: true })
          audio.addEventListener('error', () => reject(new Error('audio error')), { once: true })
        })
      } else {
        // Fallback: buffer full response then play (older browsers)
        const blob = await response.blob()
        if (abort.signal.aborted) return
        const objectUrl = URL.createObjectURL(blob)
        const audio = new Audio(objectUrl)
        audioRef.current = audio
        audio.onended = () => { resetState(); URL.revokeObjectURL(objectUrl) }
        setIsTTSLoading(false)
        try {
          await audio.play()
        } catch (playErr) {
          console.error("audio.play() failed, falling back to SpeechSynthesis", playErr)
          URL.revokeObjectURL(objectUrl); audioRef.current = null
          speakWithBrowser(message.content)
        }
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') return  // cancelled by user — no fallback
      setIsTTSLoading(false)
      setIsSpeaking(null)
      console.error("TTS API failed, falling back to SpeechSynthesis", err)
      speakWithBrowser(message.content)
    }
  }

  const handleWeatherClick = () => {
    if (!navigator.geolocation) {
      alert(t("chat.error_location_support"))
      return
    }

    setIsLoading(true)
    isAutoScrollingRef.current = true
    setTimeout(() => scrollToBottom(true), 50)

    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const { latitude, longitude } = position.coords
        const res = await fetch(`${API_BASE}/api/weather/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: 'include',
          body: JSON.stringify({ lat: latitude, lon: longitude }),
        })
        const data = await res.json()
        if (data.success) {
          setWeatherData(data.data)
          setMessages(prev => [...prev, {
            id: Date.now(),
            role: "assistant",
            content: t("chat.weather_update", {
              description: data.data.current.weather[0].description,
              temp: Math.round(data.data.current.main.temp)
            })
          }])
        }
      } catch (err) {
        console.error("Weather fetch failed", err)
      } finally {
        setIsLoading(false)
      }
    }, (err) => {
      console.error("Geolocation error", err)
      setIsLoading(false)
      alert(t("chat.error_location_perm"))
    })
  }

  const silentRefreshMessages = useCallback(async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/history/${id}/`, { credentials: 'include' })
      const data = await res.json()
      if (data.success) {
        setMessages(data.messages)
      }
    } catch {
      // silently ignore poll errors
    }
  }, [])

  const loadConversation = async (id: number) => {
    try {
      setIsLoading(true)
      setMessages([]) // Clear current messages for immediate feedback
      const res = await fetch(`${API_BASE}/api/history/${id}/`, { credentials: 'include' })
      const data = await res.json()
      if (data.success) {
        setMessages(data.messages)
        setCurrentConvId(id)
        setSidebarOpen(false)
        // Focus input after a short delay to ensure UI is ready
        setTimeout(() => inputRef.current?.focus(), 100)
      }
    } catch (err) {
      console.error("Failed to load conversation", err)
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = async (text: string, id: string | number) => {
    try {
      // Clean internal tags before copying
      const cleanText = text.split('[FARMBUDDY_REFS]')[0].trim()
      await navigator.clipboard.writeText(cleanText)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error("Failed to copy", err)
    }
  }

  useEffect(() => {
    fetchConversations()
    fetchUserProfile()
  }, [fetchConversations, fetchUserProfile])

  // Persist current conversation across page refreshes
  useEffect(() => {
    if (currentConvId) {
      localStorage.setItem('farmbuddy_conv_id', String(currentConvId))
    }
  }, [currentConvId])

  // Restore last conversation once the list is loaded
  useEffect(() => {
    if (hasRestoredConvRef.current || conversations.length === 0) return
    hasRestoredConvRef.current = true
    const savedId = localStorage.getItem('farmbuddy_conv_id')
    const target = savedId
      ? (conversations.find((c) => c.id === Number(savedId)) ?? conversations[0])
      : conversations[0]
    if (target) loadConversation(target.id)
  }, [conversations])

  // Poll for new messages every 10 s when viewing Telegram Chat
  useEffect(() => {
    if (!currentConvId) return
    const currentConv = conversations.find(c => c.id === currentConvId)
    if (currentConv?.title !== 'Telegram Chat') return

    const interval = setInterval(() => {
      silentRefreshMessages(currentConvId)
      fetchConversations()
    }, 10000)

    return () => clearInterval(interval)
  }, [currentConvId, conversations, silentRefreshMessages, fetchConversations])

  const handleSend = async () => {
    if ((!inputValue.trim() && !selectedImage) || isLoading) return

    const tempUserMsg: Message = {
      id: Date.now(),
      role: "user",
      content: inputValue || (selectedImage ? "[Plant image uploaded for analysis]" : ""),
      image_url: previewUrl || undefined
    }

    setMessages(prev => [...prev, tempUserMsg])
    const messageToSend = inputValue
    const imageToSend = selectedImage

    setInputValue("")
    setSelectedImage(null)
    setPreviewUrl(null)
    setUploadProgress(0)
    setIsLoading(true)
    isAutoScrollingRef.current = true // Force auto-scroll for new user message
    setTimeout(() => scrollToBottom(true), 50)

    try {
      let response;
      if (imageToSend) {
        const formData = new FormData()
        if (messageToSend) formData.append('message', messageToSend)
        formData.append('image', imageToSend)
        if (currentConvId) formData.append('conversation_id', currentConvId.toString())

        response = await fetch(`${API_BASE}/upload/`, {
          method: "POST",
          credentials: 'include',
          body: formData,
        })
      } else {
        response = await fetch(`${API_BASE}/send/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: 'include',
          body: JSON.stringify({
            message: messageToSend,
            conversation_id: currentConvId,
            language: preferredLanguage
          }),
        })
      }

      if (!response.body) throw new Error("No response body")

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ""
      let assistantMsgId = Date.now() + 1

      // Add placeholder for assistant message
      setMessages(prev => [...prev, { id: assistantMsgId, role: "assistant", content: "" }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split("\n").filter(l => l.trim())

        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.chunk) {
              assistantContent += data.chunk
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, content: assistantContent } : m
              ))
            }
            if (data.success) {
              if (data.conversation_id && !currentConvId) {
                setCurrentConvId(data.conversation_id)
                fetchConversations()
              }
              // Update with final content and references if any
              if (data.full_text) {
                setMessages(prev => prev.map(m =>
                  m.id === assistantMsgId ? { ...m, content: data.full_text, references: data.references } : m
                ))
              }
            }
          } catch (e) {
            console.warn("Error parsing NDJSON line", e)
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error)
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: "assistant",
        content: t("chat.error_server")
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/new/`, { method: "POST", credentials: "include" })
      const data = await res.json()
      if (data.success) {
        setMessages([])
        setCurrentConvId(data.conversation_id)
        fetchConversations()
        setSidebarOpen(false)
      }
    } catch (err) {
      console.error("Failed to create new chat", err)
    }
  }

  const handleDeleteConversation = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (!confirm(t("chat.delete_confirm"))) return

    try {
      const res = await fetch(`${API_BASE}/api/delete/${id}/`, {
        method: "POST", // Backend supports both POST and DELETE
        credentials: "include",
      })
      const data = await res.json()
      if (data.success) {
        if (currentConvId === id) {
          setMessages([])
          setCurrentConvId(null)
        }
        fetchConversations()
      }
    } catch (err) {
      console.error("Failed to delete conversation", err)
    }
  }

  const startRename = (e: React.MouseEvent, conv: ConversationItem) => {
    e.stopPropagation()
    setEditingConvId(conv.id)
    setEditingTitle(conv.title)
  }

  const handleRename = async (e: React.FormEvent | React.MouseEvent) => {
    if (e) {
      if ('preventDefault' in e) e.preventDefault()
      if ('stopPropagation' in e) e.stopPropagation()
    }
    
    if (!editingConvId || !editingTitle.trim()) return

    try {
      const res = await fetch(`${API_BASE}/api/rename/${editingConvId}/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editingTitle.trim() }),
      })
      const data = await res.json()
      if (data.success) {
        setConversations(prev =>
          prev.map(c => c.id === editingConvId ? { ...c, title: data.title } : c)
        )
        setEditingConvId(null)
      }
    } catch (err) {
      console.error("Failed to rename conversation", err)
    }
  }

  const fileInputRef = useRef<HTMLInputElement>(null)

  const onImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || isLoading) return

    setSelectedImage(file)
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)

    // Focus input to allow adding text
    setTimeout(() => inputRef.current?.focus(), 100)

    // Reset file input so same file can be selected again
    if (fileInputRef.current) fileInputRef.current.value = ""
  }
  const handleQuickAction = (action: string) => {
    setInputValue(action)
  }

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/accounts/logout/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
    } catch (err) {
      console.error("Logout failed", err)
    } finally {
      localStorage.setItem("preferred_language", "en")
      window.location.href = "/login"
    }
  }

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  useEffect(() => {
    if (!searchQuery || searchQuery.trim().length < 2) {
      setMessageSearchResults([])
      setIsSearchingMessages(false)
      return
    }
    setIsSearchingMessages(true)
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/search/?q=${encodeURIComponent(searchQuery.trim())}`,
          { credentials: 'include' }
        )
        const data = await res.json()
        if (data.success) setMessageSearchResults(data.results)
      } catch {
        // silently ignore search errors
      } finally {
        setIsSearchingMessages(false)
      }
    }, 350)
    return () => clearTimeout(timer)
  }, [searchQuery, API_BASE])

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 p-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sidebar-primary">
          <Sprout className="h-5 w-5 text-sidebar-primary-foreground" />
        </div>
        <span className="text-lg font-semibold text-sidebar-foreground">FarmBuddy</span>
      </div>

      <div className="px-4 pb-3">
        <Button
          className="w-full justify-start gap-2"
          onClick={handleNewChat}
        >
          <Plus className="h-4 w-4" />
          {t("chat.new_chat")}
        </Button>
      </div>

      {/* Search */}
      <div className="px-4 pb-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-sidebar-foreground/40 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="w-full rounded-lg border border-sidebar-border bg-sidebar-accent/40 py-2 pl-8 pr-3 text-sm text-sidebar-foreground placeholder:text-sidebar-foreground/40 outline-none focus:border-primary/50 focus:bg-sidebar-accent/60 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-sidebar-foreground/40 hover:text-sidebar-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="sidebar-scroll flex-1 overflow-y-auto overflow-x-hidden min-h-0 px-4">
        {/* Section label: RECENT when idle, CHAT NAMES when searching */}
        <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wider text-sidebar-foreground/50">
          {searchQuery ? "Chat Names" : t("chat.recent")}
        </p>
        <div className="space-y-1">
          {filteredConversations.length > 0 ? (
            filteredConversations.map((conv) => (
              <div key={conv.id} className="group relative">
                {editingConvId === conv.id ? (
                  <form
                    onSubmit={handleRename}
                    className="flex w-full items-center gap-1 rounded-lg bg-sidebar-accent px-2 py-1"
                  >
                    <Input
                      autoFocus
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      className="h-8 flex-1 rounded border border-input bg-white px-2 text-sm text-black focus-visible:ring-1 focus-visible:ring-primary"
                    />
                    <Button
                      type="submit"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0 text-green-500 hover:bg-green-500/10"
                    >
                      <SaveIcon className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0 text-red-500 hover:bg-red-500/10"
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditingConvId(null)
                      }}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </form>
                ) : (
                  <div className={cn(
                    "flex w-full items-center rounded-lg text-sm transition-colors",
                    currentConvId === conv.id
                      ? "bg-sidebar-accent"
                      : "hover:bg-sidebar-accent/50"
                  )}>
                    <button
                      onClick={() => loadConversation(conv.id)}
                      className={cn(
                        "flex min-w-0 flex-1 flex-col gap-0.5 py-2 pl-3 text-left",
                        currentConvId === conv.id
                          ? "text-sidebar-foreground"
                          : "text-sidebar-foreground/70"
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <MessageSquare className="h-4 w-4 shrink-0 opacity-60" />
                        <span className="truncate text-sm">{conv.title}</span>
                      </div>
                      <span className="pl-6 text-xs text-sidebar-foreground/50">{formatRelativeTime(conv.updated_at)}</span>
                    </button>

                    <div className="shrink-0 px-1">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            className="flex h-7 w-7 items-center justify-center rounded text-zinc-500 hover:bg-white/10 hover:text-zinc-200 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                            title="More options"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent side="right" align="start" className="w-40">
                          <DropdownMenuItem
                            className="gap-2 cursor-pointer"
                            onSelect={() => {
                              setEditingConvId(conv.id)
                              setEditingTitle(conv.title)
                            }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="gap-2 cursor-pointer text-red-500 focus:text-red-500"
                            onSelect={(e) => handleDeleteConversation(e as any, conv.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                )}
              </div>
            ))
          ) : !searchQuery ? (
            <p className="py-8 text-center text-sm text-sidebar-foreground/40">
              {t("chat.no_conversations")}
            </p>
          ) : null}
        </div>

        {/* Message search results section */}
        {searchQuery && searchQuery.trim().length >= 2 && (() => {
          const titleMatchIds = new Set(filteredConversations.map(c => c.id))
          const msgResults = messageSearchResults.filter(r => !titleMatchIds.has(r.conversation_id))
          return (
            <div className="mt-3">
              <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wider text-sidebar-foreground/50">
                {isSearchingMessages ? "Searching messages…" : `In Messages${msgResults.length > 0 ? ` (${msgResults.length})` : ''}`}
              </p>
              {!isSearchingMessages && msgResults.length === 0 && filteredConversations.length === 0 && (
                <p className="py-4 text-center text-sm text-sidebar-foreground/40">No results found</p>
              )}
              <div className="space-y-1">
                {msgResults.map((result) => (
                  <button
                    key={result.conversation_id}
                    onClick={() => loadConversation(result.conversation_id)}
                    className={cn(
                      "flex w-full min-w-0 flex-col gap-0.5 rounded-lg py-2 pl-3 pr-2 text-left transition-colors",
                      currentConvId === result.conversation_id
                        ? "bg-sidebar-accent text-sidebar-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50"
                    )}
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <MessageSquare className="h-4 w-4 shrink-0 opacity-60" />
                      <span className="truncate text-sm">{result.conversation_title}</span>
                    </div>
                    <span className="pl-6 text-xs text-sidebar-foreground/40 truncate">{result.snippet}</span>
                  </button>
                ))}
              </div>
            </div>
          )
        })()}
      </div>

      <div className="border-t border-sidebar-border p-4">
        <div className="space-y-1">
          <Link
            href="/profile"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
          >
            <User className="h-4 w-4 opacity-70" />
            {t("chat.my_farm")}
          </Link>
          <Link
            href="/settings"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
          >
            <Settings className="h-4 w-4 opacity-70" />
            {t("chat.settings")}
          </Link>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4 opacity-70" />
            ) : (
              <Moon className="h-4 w-4 opacity-70" />
            )}
            {theme === "dark" ? t("chat.light_mode") : t("chat.dark_mode")}
          </button>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-red-400 transition-colors hover:bg-sidebar-accent"
          >
            <LogOut className="h-4 w-4 opacity-70" />
            {t("chat.logout")}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-[100dvh] bg-background overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 bg-sidebar lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-72 bg-sidebar p-0">
          <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
          <SheetDescription className="sr-only">
            Access your chats, farm profile, and settings
          </SheetDescription>
          <SidebarContent />
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="flex flex-1 flex-col min-h-0">
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-4">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-sm font-medium">{t("chat.header_title")}</h1>
              <p className="text-xs text-muted-foreground">{t("chat.header_subtitle")}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="hidden lg:flex"
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
            </Button>
            <Link href="/profile">
              <Button variant="outline" size="sm" className="gap-2">
                <User className="h-4 w-4" />
                <span className="hidden sm:inline">{t("chat.my_farm")}</span>
              </Button>
            </Link>
          </div>
        </header>

        <div className="flex flex-1 flex-col overflow-hidden min-h-0 relative">
          <ScrollArea className="flex-1 min-h-0" ref={scrollAreaRef}>
            <div className="mx-auto max-w-3xl px-4 pt-20 pb-8">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center py-8">
                  <div className="mb-6 rounded-2xl bg-accent/50 p-6">
                    <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary">
                      <Sprout className="h-8 w-8 text-primary-foreground" />
                    </div>
                  </div>
                  <h2 className="mb-2 text-2xl font-bold">{t("chat.welcome_title")}</h2>
                  <p className="mb-8 max-w-md text-center text-muted-foreground">
                    {t("chat.welcome_subtitle")}
                  </p>

                  <div className="grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
                    {quickActions.map((action) => (
                      <button
                        key={action.label}
                        onClick={() => handleQuickAction(action.label)}
                        className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary hover:bg-accent"
                      >
                        <action.icon className="h-5 w-5 shrink-0 text-primary" />
                        <span className="text-sm font-medium">{action.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {messages.map((message, idx) => (
                    <div
                      key={message.id || idx}
                      className={cn(
                        "flex w-full mb-6",
                        message.role === "user" ? "justify-end" : "justify-start"
                      )}
                    >
                      <div
                        className={cn(
                          "relative max-w-[85%] rounded-3xl px-5 py-4 shadow-sm transition-all duration-300",
                          message.role === "user"
                            ? "bg-gradient-to-br from-primary via-primary/90 to-primary/80 text-primary-foreground rounded-tr-none shadow-lg shadow-primary/10"
                            : "bg-card border border-border/50 text-card-foreground rounded-tl-none hover:shadow-md"
                        )}
                      >
                        {message.image_url && (
                          <div className="mb-3 overflow-hidden rounded-2xl bg-muted/20 w-fit">
                            <img
                              src={message.image_url.startsWith('blob:') || message.image_url.startsWith('data:') || message.image_url.startsWith('http')
                                ? message.image_url
                                : `${API_BASE_URL}${message.image_url}`
                              }
                              alt="Uploaded visual"
                              className="block max-h-44 max-w-[200px] object-contain transition-transform hover:scale-[1.02] cursor-pointer"
                              onClick={() => window.open(message.image_url?.startsWith('blob:') ? message.image_url : `${API_BASE_URL}${message.image_url}`, '_blank')}
                            />
                          </div>
                        )}

                        <div className="text-sm leading-relaxed sm:text-base">
                          <FormattedMessage content={message.content} />
                        </div>

                        {message.role === "assistant" && (
                          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-4">
                            <div className="flex items-center gap-2">
                              <Button
                                variant="secondary"
                                size="sm"
                                className="h-9 gap-2 text-xs font-semibold bg-accent/50 hover:bg-accent"
                                onClick={() => playMessage(message)}
                              >
                                {isSpeaking === message.id ? (
                                  isTTSLoading ? (
                                    <>
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                      {t('loading')}
                                    </>
                                  ) : isPaused ? (
                                    <>
                                      <Play className="h-3.5 w-3.5" />
                                      {t('chat.resume')}
                                    </>
                                  ) : (
                                    <>
                                      <Pause className="h-3.5 w-3.5 animate-pulse" />
                                      {t('chat.pause')}
                                    </>
                                  )
                                ) : (
                                  <>
                                    <Mic className="h-3.5 w-3.5" />
                                    {t('chat.listen')}
                                  </>
                                )}
                              </Button>

                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-9 w-9 p-0"
                                onClick={() => copyToClipboard(message.content, message.id)}
                                title={t('chat.copy_response')}
                              >
                                {copiedId === message.id ? (
                                  <Check className="h-4 w-4 text-green-500" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                            <span className="text-[10px] text-muted-foreground italic">
                              {t('chat.response_generated_by')}
                            </span>
                          </div>
                        )}

                        {message.references && message.references.length > 0 && (
                          <div className="mt-4 rounded-2xl bg-primary/5 p-4 border border-primary/10 shadow-inner">
                            <div className="flex items-center gap-2 mb-3">
                              <Sprout className="h-4 w-4 text-primary" />
                              <p className="text-[11px] font-bold uppercase tracking-widest text-primary">{t('chat.sources_header')}</p>
                            </div>
                            <ul className="space-y-3">
                              {message.references.map((ref: any, idx: number) => (
                                <li key={idx} className="text-[12px] leading-relaxed text-muted-foreground flex gap-3 group">
                                  <div className="shrink-0 mt-1 h-1.5 w-1.5 rounded-full bg-primary/40 group-hover:bg-primary/60 transition-colors" />
                                  <span>
                                    <strong className="text-foreground/80 font-bold uppercase text-[10px] block mb-0.5 tracking-tight">
                                      {ref.type === 'profile' ? t('chat.source_profile') : t('chat.source_conversation')} ({ref.key}):
                                    </strong>{" "}
                                    {ref.explanation}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
                        <Sprout className="h-4 w-4 text-primary-foreground" />
                      </div>
                      <div className="rounded-2xl border border-border bg-card px-4 py-3">
                        <div className="flex gap-1.5">
                          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
                          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
                          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div ref={messagesEndRef} className="h-1 shrink-0" />
            </div>
          </ScrollArea>

          {showScrollButton && (
            <div className="absolute bottom-[90px] left-0 right-0 flex justify-center z-10 mx-auto max-w-3xl pointer-events-none">
              <Button
                size="icon"
                className="h-10 w-10 rounded-full shadow-md bg-background/80 hover:bg-background border border-border/50 text-foreground pointer-events-auto transition-transform hover:scale-105 active:scale-95"
                onClick={() => {
                  isAutoScrollingRef.current = true
                  scrollToBottom(true, true)
                }}
              >
                <ArrowDown className="h-5 w-5 text-primary" />
              </Button>
            </div>
          )}

          {/* Input Area */}
          <div className="shrink-0 border-t border-border bg-card p-4">
            <div className="mx-auto max-w-3xl">
              {/* Image Staging Area */}
              {previewUrl && (
                <div className="relative mb-4 group inline-block">
                  <div className="relative overflow-hidden rounded-2xl border-2 border-primary/20 shadow-xl">
                    <img
                      src={previewUrl}
                      alt="Staged"
                      className="h-32 w-auto object-cover transition-opacity duration-300 group-hover:opacity-90"
                    />
                    {isLoading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[2px]">
                        <div className="relative h-12 w-12">
                          <svg className="h-full w-full" viewBox="0 0 36 36">
                            <circle
                              className="stroke-white/20"
                              strokeWidth="3"
                              fill="transparent"
                              r="16"
                              cx="18"
                              cy="18"
                            />
                            <circle
                              className="stroke-primary animate-[dash_1.5s_ease-in-out_infinite]"
                              strokeWidth="3"
                              strokeLinecap="round"
                              strokeDasharray="100"
                              fill="transparent"
                              r="16"
                              cx="18"
                              cy="18"
                            />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <Leaf className="h-4 w-4 text-primary animate-pulse" />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  {!isLoading && (
                    <Button
                      variant="destructive"
                      size="icon"
                      className="absolute -right-2 -top-2 h-7 w-7 rounded-full shadow-lg transition-transform hover:scale-110"
                      onClick={() => {
                        setSelectedImage(null)
                        setPreviewUrl(null)
                      }}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2">
                <div className="hidden shrink-0 gap-1 sm:flex">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10 text-muted-foreground hover:text-foreground"
                    onClick={handleWeatherClick}
                  >
                    <Cloud className="h-5 w-5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10 text-muted-foreground hover:text-foreground"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <ImageIcon className="h-5 w-5" />
                  </Button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="image/*"
                    onChange={onImageSelect}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className={`h-10 w-10 ${isRecording ? 'text-red-500 bg-red-50' : 'text-muted-foreground'} hover:text-foreground`}
                    onClick={handleMicClick}
                  >
                    <Mic className={`h-5 w-5 ${isRecording ? 'animate-pulse' : ''}`} />
                  </Button>
                </div>

                <div className="relative flex-1">
                  <Input
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        handleSend()
                      }
                    }}
                    placeholder={isTranscribing ? "Transcribing..." : t('chat.input_placeholder_alt')}
                    className="h-12 w-full rounded-xl border-border bg-background pr-4 pl-4 text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                <Button
                  onClick={handleSend}
                  disabled={(!inputValue.trim() && !selectedImage) || isLoading}
                  size="icon"
                  className="h-12 w-12 shrink-0 rounded-xl"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
              {/* Mobile recording / transcribing indicator */}
              {(isRecording || isTranscribing) && (
                <div className={`mt-3 flex items-center justify-center gap-2 rounded-lg px-3 py-2 sm:hidden border ${isTranscribing ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'}`}>
                  <span className={`h-2 w-2 rounded-full animate-pulse ${isTranscribing ? 'bg-yellow-500' : 'bg-red-500'}`} />
                  <span className={`text-xs font-medium ${isTranscribing ? 'text-yellow-700' : 'text-red-600'}`}>
                    {isTranscribing ? "Transcribing... please wait" : "Recording... tap mic to stop"}
                  </span>
                </div>
              )}
              {/* Mobile action buttons */}
              <div className="mx-auto mt-3 flex max-w-3xl justify-center gap-2 sm:hidden">
                <Button variant="outline" size="icon" className="h-9 w-9 text-muted-foreground" onClick={handleWeatherClick}>
                  <Cloud className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="h-9 w-9 text-muted-foreground" onClick={() => fileInputRef.current?.click()}>
                  <ImageIcon className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className={`h-9 w-9 ${isRecording ? 'text-red-500 border-red-300 bg-red-50' : 'text-muted-foreground'}`}
                  onClick={handleMicClick}
                >
                  <Mic className={`h-4 w-4 ${isRecording ? 'animate-pulse' : ''}`} />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
