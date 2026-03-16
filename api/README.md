# Minhocao Wiki API

Backend FastAPI responsavel por autenticacao, gerenciamento de conversas e respostas RAG em streaming.

## Documentacao de Endpoints

Documentacao completa e atualizada da API:

- `api/docs/api-doc.md`

Use esse arquivo como referencia principal de contratos HTTP, exemplos e codigos de erro.

## Responsabilidades da API

1. Cadastro e login com JWT.
2. Login com Google (`/auth/google`).
3. CRUD basico de conversas (criar, listar, obter mensagens, deletar).
4. Endpoint de chat em streaming (`/chat`).
5. Persistencia em PostgreSQL.
6. Integracao com pipeline RAG (LangChain + Pinecone + OpenAI).

## Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy + psycopg2
- LangChain
- Pinecone
- OpenAI

Dependencias completas em `api/requirements.txt`.

## Estrutura

```text
api/
├── app/
│   ├── main.py                 # Inicializacao FastAPI
│   ├── config.py               # Leitura de config/env
│   ├── auth.py                 # JWT e password hashing
│   ├── models.py               # Modelos SQLAlchemy
│   ├── routers/
│   │   ├── auth.py
│   │   ├── conversations.py
│   │   └── chat.py
│   └── services/
│       ├── chat_service.py
│       └── conversation_service.py
├── docs/
│   └── api-doc.md
├── ingestion/
│   └── ingest_documents.py
├── tests/
└── config.yaml.exemple
```

## Configuracao

Existem duas fontes de configuracao:

1. `config.yaml` (base)
2. Variaveis de ambiente (sobrescrevem o `config.yaml`)

Campos mais importantes:

- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `INDEX_NAME`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_ID`

Exemplo base em `api/config.yaml.exemple`.

## Execucao Local (sem Docker)

1. Criar venv e instalar dependencias:

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

2. Ajustar `config.yaml` (ou env vars).

3. Subir API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Acessar Swagger: `http://localhost:8000/docs`.

## Execucao com Docker Compose

No root do projeto:

```bash
docker compose up -d --build api db
```

## Ingestao de Documentos

Comando:

```bash
cd api
python ingestion/ingest_documents.py
```

Esse processo prepara o indice vetorial e registra auditoria em `api/logs/`.

## Testes

```bash
cd api
pytest
```
