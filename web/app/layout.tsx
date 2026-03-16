import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Providers } from '@/components/providers'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Minhocão Wiki',
  description: 'Interface de chat para RAG com controle de parâmetros do LLM',
  icons: {
    icon: [
      {
        url: '/minhocao_wiki.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/minhocao_wiki.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/minhocao_wiki.png',
        type: 'image/svg+xml',
      },
    ],
    apple: '/minhocao_wiki.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          {children}
        </Providers>
        <Analytics />
      </body>
    </html>
  )
}
