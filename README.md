# Minhocao Wiki

Plataforma de perguntas e respostas com RAG (Retrieval-Augmented Generation) para conteudos da UnB.

Este repositorio e composto por:

1. `api/`: FastAPI com autenticacao JWT, chat com streaming e persistencia em PostgreSQL.
2. `web/`: Next.js com login, historico de conversas e interface de chat.
3. `docker-compose.yml`: ambiente local com `db`, `pgadmin`, `api`, `web` e `ingest-worker`.

## Visao Geral

Fluxo principal:

1. Usuario autentica por email/senha ou Google.
2. Frontend cria ou seleciona uma conversa.
3. Frontend envia pergunta para `POST /chat` (via rotas proxy em `web/app/api/*`).
4. API consulta historico, monta contexto RAG e retorna resposta em streaming.
5. Mensagens sao persistidas no PostgreSQL.

## Arquitetura

```text
Browser (Next.js UI)
   |
   | HTTP (rotas app/api/*)
   v
Web Container (Next.js)
   |
   | HTTP interno
   v
API Container (FastAPI)
   |\
   | \__ PostgreSQL (usuarios, conversas, mensagens)
   |
   \____ OpenAI + Pinecone (RAG)
         \___ Google tokeninfo (login Google)

Ingestao assincrona (servico separado): ingest-worker
```

## Stack Tecnologica

- Backend: Python 3.11, FastAPI, SQLAlchemy, LangChain, Pinecone, OpenAI.
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui.
- Banco: PostgreSQL 16.
- Infra: Docker Compose.
- Auth: JWT + Google Identity Services.

## Pre-requisitos

1. Docker e Docker Compose.
2. Chaves de API para OpenAI e Pinecone.
3. OAuth Client ID do Google (opcional, recomendado para login social).
4. Arquivo `api/config.yaml` com parametros de RAG.

## Setup Rapido (Docker)

1. Criar o arquivo de ambiente na raiz:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Preencher no `.env`:

- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- opcionalmente `DATABASE_URL`

3. Garantir que `api/config.yaml` exista (pode copiar de `api/config.yaml.exemple`) e contenha:

- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `INDEX_NAME`

4. Subir os servicos:

```bash
docker compose up -d --build
```

5. Acessar:

- Web: `http://localhost:3000`
- API Swagger: `http://localhost:8000/docs`
- pgAdmin: `http://localhost:5050`

## Servico de Ingestao

A indexacao RAG roda no servico `ingest-worker`, separado da API.

- Intervalo padrao: `INGEST_INTERVAL_SECONDS=7200` (2h).
- Logs em tempo real:

```bash
docker compose logs -f ingest-worker
```

- Execucao manual:

```bash
docker compose run --rm ingest-worker python ingestion/ingest_documents.py
```

Observacoes importantes:

- O worker espera `api/unb.zip` montado como `/app/unb.zip`.
- Auditorias e manifestos sao salvos em `api/logs/`.

## Variaveis de Ambiente (Raiz)

Arquivo: `.env`

- `DATABASE_URL`: conexao com PostgreSQL usada pela API e pelo worker.
- `JWT_SECRET_KEY`: segredo de assinatura JWT.
- `GOOGLE_CLIENT_ID`: client id OAuth consumido pela API e injetado no build do web.

## Login com Google (Checklist)

No Google Cloud Console:

1. Adicionar `http://localhost:3000` em `Authorized JavaScript origins`.
2. Usar o mesmo client id em `GOOGLE_CLIENT_ID`.

## Testes

Backend:

```bash
cd api
pytest
```

Frontend:

```bash
cd web
pnpm lint
pnpm build
```

## Documentacao por Modulo

- Backend: `api/README.md`
- Frontend: `web/README.md`
- Endpoints da API: `api/docs/api-doc.md`
- Operacao de ingestao: `api/docs/ingest-instruction.md`

## Troubleshooting

1. Erro `Google authentication is not configured`:
   confirme `GOOGLE_CLIENT_ID` no `.env` e refaca `docker compose up -d --build web api`.
2. Erro de conexao com banco:
   confirme `DATABASE_URL` e status do servico `db`.
3. Sem respostas RAG:
   valide `OPENAI_API_KEY`, `PINECONE_API_KEY`, `INDEX_NAME` e os logs do `ingest-worker`.
