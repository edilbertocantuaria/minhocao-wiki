# Minhocao Wiki Web

Frontend Next.js da aplicacao, com autenticacao, historico de conversas e interface de chat em streaming.

## O que este modulo faz

1. Fluxo de login/cadastro por email e Google.
2. Consumo da API via rotas proxy em `app/api/*`.
3. Renderizacao incremental da resposta de chat (streaming).
4. Sidebar com historico de conversas.

## Stack

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui + Radix UI

## Estrutura

```text
web/
├── app/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   ├── page.tsx
│   └── api/
│       ├── auth/
│       ├── chat/
│       └── conversations/
├── components/
│   ├── chat-interface.tsx
│   ├── chat-sidebar.tsx
│   ├── chat-input.tsx
│   └── google-signin-button.tsx
├── contexts/
│   └── auth-context.tsx
└── package.json
```

## Variaveis de Ambiente

Arquivo local: `web/.env.local`

Exemplo:

```dotenv
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

Observacao:

- Em Docker, `NEXT_PUBLIC_GOOGLE_CLIENT_ID` entra no build via `ARG` no `Dockerfile` e `docker-compose.yml`.

## Rodando em Desenvolvimento

```bash
cd web
pnpm install
pnpm dev
```

Acesse: `http://localhost:3000`.

## Rodando com Docker Compose

No root:

```bash
docker compose up -d --build web api db
```

## Fluxo de Integracao com API

1. O browser chama rotas internas Next (`/api/...`).
2. Essas rotas fazem proxy para `http://api:8000` no ambiente Docker.
3. Token JWT fica em `sessionStorage` no cliente.
4. Requisicoes autenticadas incluem `Authorization: Bearer <token>`.

## Build e Lint

```bash
cd web
pnpm lint
pnpm build
pnpm start
```
