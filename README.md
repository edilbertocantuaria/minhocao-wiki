# Minhocao Wiki

Plataforma de perguntas e respostas com RAG (Retrieval-Augmented Generation) para conteudos da UnB, composta por:

1. `api/` com FastAPI, autenticacao JWT, chat com streaming e persistencia em PostgreSQL.
2. `web/` com Next.js para login, historico de conversas e interface de chat.
3. Infra local via Docker Compose com `db`, `pgadmin`, `api` e `web`.

## Visao Geral

O fluxo principal da aplicacao:

1. Usuario autentica por email/senha ou Google.
2. Frontend cria/seleciona conversa.
3. Frontend envia pergunta para `POST /chat`.
4. API consulta historico da conversa, monta contexto RAG e transmite resposta em streaming.
5. Pergunta e resposta sao salvas no banco.

## Arquitetura

```text
Browser (Next.js UI)
   |
   | HTTP (app/api/* proxy)
   v
Web Container (Next.js 16)
   |
   | HTTP interno
   v
API Container (FastAPI)
   |\
   | \__ PostgreSQL (usuarios, conversas, mensagens)
   |
   \____ OpenAI + Pinecone (RAG)
         \___ Google tokeninfo (login Google)
```

## Stack Tecnologica

- Backend: Python 3.11, FastAPI, SQLAlchemy, LangChain, Pinecone, OpenAI.
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui.
- Banco: PostgreSQL 16.
- Infra: Docker Compose.
- Auth: JWT (email/senha) + Google Identity Services.

## Estrutura do Projeto

```text
minhocao-wiki/
├── api/                  # Backend FastAPI e pipeline de ingestao
├── web/                  # Frontend Next.js
├── docker-compose.yml    # Orquestracao local
├── .env.example          # Variaveis globais usadas no compose
└── README.md
```

## Pre-requisitos

1. Docker e Docker Compose.
2. Conta OpenAI (API key).
3. Conta Pinecone (API key e index).
4. OAuth Client ID do Google (opcional, mas recomendado para login social).

## Setup Rapido (Docker)

1. Copie o template de ambiente:

```bash
cp .env.example .env
```

2. Preencha `JWT_SECRET_KEY` e `GOOGLE_CLIENT_ID` no arquivo `.env`.

3. Garanta que `api/config.yaml` tenha chaves de RAG (`OPENAI_API_KEY`, `PINECONE_API_KEY`, `INDEX_NAME`).

4. Suba os servicos:

```bash
docker compose up -d --build
```

5. A API sobe imediatamente e a ingestao roda em paralelo no servico `ingest-worker` a cada 2 horas.

Para acompanhar:

```bash
docker compose logs -f ingest-worker
```

6. Acesse:

- Web: `http://localhost:3000`
- API Swagger: `http://localhost:8000/docs`
- pgAdmin: `http://localhost:5050`

## Variaveis de Ambiente (Root)

Arquivo: `.env`

- `DATABASE_URL`: URL do PostgreSQL para a API no container.
- `JWT_SECRET_KEY`: segredo para assinar JWT.
- `GOOGLE_CLIENT_ID`: client id OAuth usado pela API e pelo build do web.

Observação importante:

- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` no frontend e injetado no build via `docker-compose.yml` com valor de `GOOGLE_CLIENT_ID`.
- Nunca commitar `.env`.

## Login com Google (Checklist)

No Google Cloud Console (OAuth Client ID):

1. Adicionar `http://localhost:3000` em `Authorized JavaScript origins`.
2. Usar o mesmo client id no `.env` (`GOOGLE_CLIENT_ID`).

## Ingestao de Documentos (RAG)

A ingestao roda a partir de `api/ingestion/ingest_documents.py`.

Fluxo:

1. Extracao de documentos.
2. Chunking.
3. Geracao de embeddings.
4. Escrita no indice Pinecone.

Comando (a partir de `api/`):

```bash
python ingestion/ingest_documents.py
```

No Docker Compose, a ingestao ocorre de forma assincrona no servico `ingest-worker` (padrao: a cada 2h), sem bloquear a API.

## Documentacao por Modulo

- Backend: `api/README.md`
- Frontend: `web/README.md`
- API endpoints detalhados: `api/docs/api-doc.md`

## Testes

Backend:

```bash
cd api
pytest
```

Frontend (lint):

```bash
cd web
pnpm lint
```

## Troubleshooting

1. Erro `Google Login não configurado`: confirme `GOOGLE_CLIENT_ID` no `.env` e refaca `docker compose build web api`.
2. Erro de DB na API: confirme `DATABASE_URL` e se `db` esta em execucao no compose.
3. Sem respostas do RAG: valide `OPENAI_API_KEY`, `PINECONE_API_KEY` e indexacao.
