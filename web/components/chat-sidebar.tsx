'use client'

import { useState } from 'react'
import { PanelLeftClose, PanelLeft, Plus, MessageSquare, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Spinner } from '@/components/ui/spinner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { cn } from '@/lib/utils'

export interface ChatHistory {
  id: string
  title: string
  createdAt: Date
}

interface ChatSidebarProps {
  isOpen: boolean
  onToggle: () => void
  history: ChatHistory[]
  currentChatId: string | null
  onSelectChat: (id: string) => void
  onNewChat: () => void
  onDeleteChat: (id: string) => void
  isLoading?: boolean
}

export function ChatSidebar({
  isOpen,
  onToggle,
  history,
  currentChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  isLoading = false,
}: ChatSidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    await onDeleteChat(id)
    setDeletingId(null)
  }

  return (
    <>
      {/* Toggle button when closed */}
      {!isOpen && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="fixed left-4 top-4 z-50 text-muted-foreground hover:text-foreground"
        >
          <PanelLeft className="size-5" />
          <span className="sr-only">Abrir sidebar</span>
        </Button>
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-full bg-sidebar border-r border-sidebar-border transition-all duration-300 ease-in-out flex flex-col',
          isOpen ? 'w-64' : 'w-0 overflow-hidden'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-sidebar-border">
          <h2 className="font-semibold text-sidebar-foreground">Historico</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="text-sidebar-foreground hover:text-sidebar-primary"
          >
            <PanelLeftClose className="size-5" />
            <span className="sr-only">Fechar sidebar</span>
          </Button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Button
            onClick={onNewChat}
            variant="outline"
            className="w-full justify-start gap-2 bg-sidebar-accent text-sidebar-accent-foreground border-sidebar-border hover:bg-sidebar-primary hover:text-sidebar-primary-foreground"
          >
            <Plus className="size-4" />
            Nova conversa
          </Button>
        </div>

        {/* Chat History */}
        <ScrollArea className="flex-1 px-3">
          <div className="flex flex-col gap-1 pb-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner className="size-5 text-sidebar-foreground/70" />
              </div>
            ) : history.length === 0 ? (
              <p className="text-sm text-sidebar-foreground/70 text-center py-8">
                Nenhuma conversa ainda
              </p>
            ) : (
              history.map((chat) => (
                <div
                  key={chat.id}
                  className={cn(
                    'group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer',
                    currentChatId === chat.id
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                  )}
                  onClick={() => onSelectChat(chat.id)}
                  onMouseEnter={() => setHoveredId(chat.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <MessageSquare className="size-4 shrink-0" />
                  <span className="truncate flex-1">{chat.title}</span>
                  {(hoveredId === chat.id || currentChatId === chat.id) && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive shrink-0"
                          onClick={(e) => e.stopPropagation()}
                          disabled={deletingId === chat.id}
                        >
                          {deletingId === chat.id ? (
                            <Spinner className="size-3" />
                          ) : (
                            <Trash2 className="size-3" />
                          )}
                          <span className="sr-only">Excluir conversa</span>
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Excluir conversa</AlertDialogTitle>
                          <AlertDialogDescription>
                            Tem certeza que deseja excluir esta conversa? Esta acao nao pode ser desfeita e todas as mensagens serao perdidas.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancelar</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDelete(chat.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Excluir
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>
    </>
  )
}
