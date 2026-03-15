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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restaurar sessão do sessionStorage - apenas no cliente
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const storedToken = sessionStorage.getItem(TOKEN_KEY)
        const storedUser = sessionStorage.getItem(USER_KEY)

        if (storedToken && storedUser) {
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
        }
      }
    } catch {
      // Ignore errors when sessionStorage is unavailable
    } finally {
      setIsLoading(false)
    }
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

    sessionStorage.setItem(TOKEN_KEY, accessToken)
    sessionStorage.setItem(USER_KEY, JSON.stringify(userData))
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
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
  }, [])

  // Restaurar sessão do sessionStorage - apenas no cliente
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const storedToken = sessionStorage.getItem(TOKEN_KEY)
        const storedUser = sessionStorage.getItem(USER_KEY)

        if (storedToken && storedUser) {
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
        }
      }
    } catch {
      // Ignore errors when sessionStorage is unavailable
    } finally {
      setIsLoading(false)
    }
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
