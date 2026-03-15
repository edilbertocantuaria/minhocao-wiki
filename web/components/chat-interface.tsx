'use client'

import { useState, useRef, useEffect } from 'react'
import { Sparkles } from 'lucide-react'
import { ChatSidebar, type ChatHistory } from './chat-sidebar'
import { ChatMessage, type Message } from './chat-message'
import { ChatInput } from './chat-input'
import { ParametersPanel } from './parameters-panel'
import { ThemeToggle } from './theme-toggle'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

export function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [messages, setMessages] = useState<Message[]>([])
  const [chatMessages, setChatMessages] = useState<Record<string, Message[]>>({})
  const [isLoading, setIsLoading] = useState(false)
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

  const syncMessagesForChat = (chatId: string, nextMessages: Message[]) => {
    setChatMessages((prev) => ({
      ...prev,
      [chatId]: nextMessages,
    }))

    if (currentChatIdRef.current === chatId) {
      setMessages(nextMessages)
    }
  }

  const handleNewChat = () => {
    const newId = Date.now().toString()
    setCurrentChatId(newId)
    setMessages([])
    setChatMessages((prev) => ({
      ...prev,
      [newId]: [],
    }))
  }

  const handleSelectChat = (id: string) => {
    setCurrentChatId(id)
    setMessages(chatMessages[id] ?? [])
  }

  const handleDeleteChat = (id: string) => {
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

  const handleSendMessage = async (content: string) => {
    const chatId = currentChatId || Date.now().toString()
    const existingMessages = chatMessages[chatId] ?? []

    if (!currentChatId) {
      setCurrentChatId(chatId)
    }

    if (!history.find((chat) => chat.id === chatId)) {
      setHistory((prev) => [
        {
          id: chatId,
          title: content.slice(0, 30) + (content.length > 30 ? '...' : ''),
          createdAt: new Date(),
        },
        ...prev,
      ])
    }

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

    currentChatIdRef.current = chatId
    syncMessagesForChat(chatId, nextMessages)
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: chatId,
          question: content,
          ...parameters,
        }),
      })

      if (!response.ok) {
        let errorMessage = 'Nao foi possivel obter resposta da API.'

        try {
          const errorPayload = (await response.json()) as { error?: string }
          if (errorPayload.error) {
            errorMessage = errorPayload.error
          }
        } catch {
          const fallbackText = await response.text()
          if (fallbackText) {
            errorMessage = fallbackText
          }
        }

        throw new Error(errorMessage)
      }

      if (!response.body) {
        throw new Error('A API nao retornou corpo de resposta.')
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
            <Sparkles className="size-5 text-primary" />
            <h1 className="font-semibold text-foreground">RAG Chat</h1>
          </div>
          <div className="flex items-center gap-1">
            <ParametersPanel
              parameters={parameters}
              onParametersChange={setParameters}
            />
            <ThemeToggle />
          </div>
        </header>

        {/* Messages Area */}
        <ScrollArea className="flex-1">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
                <div className="size-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <Sparkles className="size-8 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground text-center text-balance">
                  Como posso ajudar você hoje?
                </h2>
                <p className="text-muted-foreground text-center max-w-md text-balance">
                  Faça uma pergunta ou inicie uma conversa para consultar a API
                  RAG conectada ao backend local.
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
