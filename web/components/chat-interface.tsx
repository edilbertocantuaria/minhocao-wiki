'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Sparkles, LogOut } from 'lucide-react'
import { useAuth } from '@/contexts/auth-context'
import { ChatSidebar, type ChatHistory } from './chat-sidebar'
import { ChatMessage, type Message } from './chat-message'
import { ChatInput } from './chat-input'
import { ParametersPanel } from './parameters-panel'
import { ThemeToggle } from './theme-toggle'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

interface APIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface APIConversation {
  id: string
  title: string | null
  created_at: string
}

export function ChatInterface() {
  const router = useRouter()
  const { token, isLoading: authLoading, isAuthenticated, logout, user } = useAuth()

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [messages, setMessages] = useState<Message[]>([])
  const [chatMessages, setChatMessages] = useState<Record<string, Message[]>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingConversations, setIsLoadingConversations] = useState(true)
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [history, setHistory] = useState<ChatHistory[]>([])
  const [parameters, setParameters] = useState({
    frequency_penalty: 0,
    presence_penalty: 0,
    temperature: 0.7,
    max_tokens: 1024,
    n: 1,
    seed: 0,
    stop: '',
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const currentChatIdRef = useRef<string | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    currentChatIdRef.current = currentChatId
  }, [currentChatId])

  // Redirecionar para login se não autenticado
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  // Carregar conversas do backend
  const loadConversations = useCallback(async () => {
    if (!token) return

    setIsLoadingConversations(true)

    try {
      const response = await fetch('/api/conversations', {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (response.status === 401) {
        logout()
        return
      }

      if (response.ok) {
        const conversations: APIConversation[] = await response.json()
        setHistory(
          conversations.map((conv) => ({
            id: conv.id,
            title: conv.title || 'Conversa sem titulo',
            createdAt: new Date(conv.created_at),
          }))
        )
      }
    } catch (error) {
      console.error('Erro ao carregar conversas:', error)
    } finally {
      setIsLoadingConversations(false)
    }
  }, [token, logout])

  useEffect(() => {
    if (isAuthenticated && token) {
      loadConversations()
    }
  }, [isAuthenticated, token, loadConversations])

  // Carregar mensagens de uma conversa
  const loadMessages = useCallback(async (conversationId: string) => {
    if (!token) return

    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (response.status === 401) {
        logout()
        return
      }

      if (response.ok) {
        const apiMessages: APIMessage[] = await response.json()
        const formattedMessages: Message[] = apiMessages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
        }))

        setChatMessages((prev) => ({
          ...prev,
          [conversationId]: formattedMessages,
        }))

        if (currentChatIdRef.current === conversationId) {
          setMessages(formattedMessages)
        }
      }
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
    }
  }, [token, logout])

  const syncMessagesForChat = (chatId: string, nextMessages: Message[]) => {
    setChatMessages((prev) => ({
      ...prev,
      [chatId]: nextMessages,
    }))

    if (currentChatIdRef.current === chatId) {
      setMessages(nextMessages)
    }
  }

  const syncConversationTitle = useCallback(async (conversationId: string) => {
    if (!token) return

    try {
      const response = await fetch('/api/conversations', {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) return

      const conversations: APIConversation[] = await response.json()
      const target = conversations.find((conv) => conv.id === conversationId)
      if (!target) return

      setHistory((prev) =>
        prev.map((chat) =>
          chat.id === conversationId
            ? {
                ...chat,
                title: target.title || chat.title,
              }
            : chat
        )
      )
    } catch (error) {
      console.error('Erro ao sincronizar titulo da conversa:', error)
    }
  }, [token, logout])

  const handleNewChat = async () => {
    setCurrentChatId(null)
    currentChatIdRef.current = null
    setMessages([])
  }

  const handleSelectChat = async (id: string) => {
    setCurrentChatId(id)
    currentChatIdRef.current = id

    if (chatMessages[id]) {
      setMessages(chatMessages[id])
    } else {
      setMessages([])
      await loadMessages(id)
    }
  }

  const handleDeleteChat = async (id: string) => {
    if (!token) return

    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (response.status === 401) {
        logout()
        return
      }

      if (response.ok || response.status === 204) {
        setHistory((prev) => prev.filter((chat) => chat.id !== id))
        setChatMessages((prev) => {
          const nextState = { ...prev }
          delete nextState[id]
          return nextState
        })

        if (currentChatId === id) {
          setCurrentChatId(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Erro ao deletar conversa:', error)
    }
  }

  const handleSendMessage = async (content: string) => {
    if (!token) return

    let chatId = currentChatId

    // Se não há conversa atual, criar uma nova
    if (!chatId) {
      try {
        const response = await fetch('/api/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ title: null }),
        })

        if (response.status === 401) {
          logout()
          return
        }

        if (response.ok) {
          const conversation: APIConversation = await response.json()
          chatId = conversation.id

          const newChat: ChatHistory = {
            id: conversation.id,
            title: 'Gerando titulo...',
            createdAt: new Date(conversation.created_at),
          }

          setHistory((prev) => [newChat, ...prev])
          setCurrentChatId(chatId)
          currentChatIdRef.current = chatId
        } else {
          throw new Error('Erro ao criar conversa')
        }
      } catch (error) {
        console.error('Erro ao criar conversa:', error)
        return
      }
    }

    const existingMessages = chatMessages[chatId] ?? []

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
    }

    const assistantMessageId = `${Date.now()}-assistant`
    const assistantPlaceholder: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    }

    const nextMessages = [...existingMessages, userMessage, assistantPlaceholder]

    syncMessagesForChat(chatId, nextMessages)
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: chatId,
          question: content,
          ...parameters,
        }),
      })

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        let errorMessage = 'Nao foi possivel obter resposta da API.'

        try {
          const errorPayload = (await response.json()) as { error?: string; detail?: string }
          if (errorPayload.error) {
            errorMessage = errorPayload.error
          } else if (errorPayload.detail) {
            errorMessage = errorPayload.detail
          }
        } catch {
          const fallbackText = await response.text()
          if (fallbackText) {
            errorMessage = fallbackText
          }
        }

        throw new Error(errorMessage)
      }

      await syncConversationTitle(chatId)

      if (!response.body) {
        throw new Error('A API não retornou corpo de resposta.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        fullResponse += decoder.decode(value, { stream: true })

        syncMessagesForChat(
          chatId,
          nextMessages.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: fullResponse }
              : message
          )
        )
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Ocorreu um erro inesperado ao consultar a API.'

      syncMessagesForChat(
        chatId,
        nextMessages.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: `Erro ao consultar a API: ${errorMessage}`,
              }
            : message
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  // Loading screen
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Spinner className="size-8" />
      </div>
    )
  }

  // Se não está autenticado, não renderizar nada (será redirecionado)
  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <ChatSidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        history={history}
        currentChatId={currentChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        isLoading={isLoadingConversations}
      />

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 flex flex-col transition-all duration-300 ease-in-out',
          sidebarOpen ? 'ml-64' : 'ml-0'
        )}
      >
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-30">
          <div className="flex items-center gap-2">
            {!sidebarOpen && <div className="w-10" />}
            <h1 className="font-semibold text-foreground">Minhocão Wiki</h1>
          </div>
          <div className="flex items-center gap-1">
            {user?.email && (
              <span className="text-sm text-muted-foreground mr-2 hidden sm:inline">
                {user.email}
              </span>
            )}
            <ParametersPanel
              parameters={parameters}
              onParametersChange={setParameters}
            />
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground"
            >
              <LogOut className="size-5" />
              <span className="sr-only">Sair</span>
            </Button>
          </div>
        </header>

        {/* Messages Area */}
        <ScrollArea className="flex-1">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
                {/* <div className="size-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <Sparkles className="size-8 text-primary" />
                </div> */}
                <img src="/minhocao_wiki.png" alt="Minhocão Wiki" className="size-45" />
                <h2 className="text-2xl font-semibold text-foreground text-center text-balance">
                  Como posso ajudar você hoje?
                </h2>
                <p className="text-muted-foreground text-center max-w-md text-balance">
                  Faça uma pergunta sobre a UnB e eu responderei com base nos documentos disponíveis.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border/50 pb-4">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                <div ref={messagesEndRef} className="h-3" />
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t border-border bg-background/80 backdrop-blur-sm px-4 py-3">
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSend={handleSendMessage}
              isLoading={isLoading}
              disabled={false}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
