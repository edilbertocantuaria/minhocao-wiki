# Minhocao Wiki API

Backend FastAPI responsavel por autenticacao, gerenciamento de conversas e respostas RAG em streaming.

## Escopo deste modulo

1. Cadastro e login com JWT.
2. Login com Google (`POST /auth/google`).
3. Conversas: criar, listar, obter mensagens e deletar.
4. Chat com streaming (`POST /chat`).
5. Persistencia em PostgreSQL.
6. Integracao RAG com OpenAI + Pinecone.

## Documentacao de referencia

- Endpoints e contratos HTTP: `docs/api-doc.md`
- Operacao de ingestao: `docs/ingest-instruction.md`

## Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy + psycopg2
- LangChain
- Pinecone
- OpenAI

Dependencias completas em `requirements.txt`.

## Estrutura principal

```text
api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── models.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── conversations.py
│   │   └── chat.py
│   └── services/
│       ├── chat_service.py
│       └── conversation_service.py
├── ingestion/
│   └── ingest_documents.py
├── docs/
├── logs/
└── tests/
```

## Configuracao

A API le configuracao em duas camadas:

1. `config.yaml`
2. Variaveis de ambiente (com prioridade)

Campos obrigatorios para RAG:

- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `INDEX_NAME`

Campos importantes de runtime:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM` (padrao: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (padrao: `60`)
- `GOOGLE_CLIENT_ID`

Use `config.yaml.exemple` como base.

## Execucao local (sem Docker)

1. Criar ambiente e instalar dependencias:

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```

2. Criar `config.yaml` (copiando de `config.yaml.exemple`) e preencher as chaves.

3. Subir API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Validar:

- Swagger: `http://localhost:8000/docs`
- Health basico: `http://localhost:8000/health`

## Execucao com Docker Compose

No diretorio raiz do repositorio:

```bash
docker compose up -d --build
```

Comportamento atual:

- O container `api` sobe rapidamente e fica disponivel.
- A ingestao roda em paralelo no servico `ingest-worker`.
- Intervalo padrao do worker: `INGEST_INTERVAL_SECONDS=7200`.

Para acompanhar ingestao:

```bash
docker compose logs -f ingest-worker
```

## Ingestao RAG

Execucao manual (a partir de `api/`):

```bash
python ingestion/ingest_documents.py
```

Execucao manual via compose:

```bash
docker compose run --rm ingest-worker python ingestion/ingest_documents.py
```

Comportamento incremental:

- Novo PDF: adiciona vetores.
- PDF atualizado: remove vetores antigos do arquivo e reindexa.
- PDF removido: remove vetores desse arquivo.
- PDF inalterado: nao reprocessa.

Arquivos de auditoria gerados em `logs/`:

- `ingestion_manifest.json`
- `ingestion_audit_latest.json`
- `ingestion_audit.jsonl`
- `ingestion_YYYYMMDD_HHMMSS.txt`

Flags uteis:

```bash
INGEST_FORCE_RECREATE_INDEX=true python ingestion/ingest_documents.py
INGEST_FORCE_EXTRACT=true python ingestion/ingest_documents.py
```

## Testes

```bash
cd api
pytest
```

## Troubleshooting rapido

1. `Database unavailable`:
	valide `DATABASE_URL` e conectividade com PostgreSQL.
2. `Google authentication is not configured`:
	configure `GOOGLE_CLIENT_ID`.
3. Erro de indexacao RAG:
	confira chaves OpenAI/Pinecone e logs em `logs/`.
