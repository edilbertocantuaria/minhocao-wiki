'use client'

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface User {
  id: string
  email: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'minhocao_access_token'
const USER_KEY = 'minhocao_user'

function safeGetItem(key: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    return sessionStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSetItem(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // Ignorar erros de storage
  }
}

function safeRemoveItem(key: string): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(key)
  } catch {
    // Ignorar erros de storage
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restaurar sessão do sessionStorage apenas no cliente
  useEffect(() => {
    const storedToken = safeGetItem(TOKEN_KEY)
    const storedUser = safeGetItem(USER_KEY)

    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
      } catch {
        // JSON invalido, limpar storage
        safeRemoveItem(TOKEN_KEY)
        safeRemoveItem(USER_KEY)
      }
    }

    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Erro ao fazer login')
    }

    const data = await response.json()
    const accessToken = data.access_token

    // Decodificar JWT para obter informações do usuário
    const payload = JSON.parse(atob(accessToken.split('.')[1]))
    const userData: User = {
      id: payload.sub,
      email: payload.email || email,
      created_at: new Date().toISOString(),
    }

    setToken(accessToken)
    setUser(userData)

    safeSetItem(TOKEN_KEY, accessToken)
    safeSetItem(USER_KEY, JSON.stringify(userData))
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Erro ao criar conta')
    }

    // Após registro bem-sucedido, fazer login automaticamente
    await login(email, password)
  }, [login])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    safeRemoveItem(TOKEN_KEY)
    safeRemoveItem(USER_KEY)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}
