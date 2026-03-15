# Minhocão Wiki - API

API de **busca semântica com RAG (Retrieval Augmented Generation)** construída em Python.

A API recebe uma pergunta via HTTP, busca documentos relevantes em um banco vetorial e usa um modelo de linguagem para gerar a resposta.

Funcionalidades implementadas:

* API REST
* Chat com histórico de conversa
* Query rewriting (perguntas dependentes de contexto)
* Streaming de resposta
* Retorno de fontes dos documentos
* Logging para experimentos de TCC

---

# 1. Pré-requisitos

Antes de rodar o projeto você precisa instalar:

* Python 3.10 ou superior
* pip (gerenciador de pacotes Python)
* Conta na OpenAI
* Conta no Pinecone

Verifique o Python:

```
python --version
```

ou

```
python3 --version
```

Se aparecer algo como:

```
Python 3.11.5
```

então está ok.

---

# 2. Estrutura do projeto

Estrutura esperada:

```
minhocao-wiki
│
└── api
    │
    ├── app
    │   ├── main.py
    │   ├── rag_chain.py
    │   ├── prompts.py
    │   ├── memory.py
    │   ├── logger.py
    │   ├── models.py
    │   └── config.py
    │
    ├── ingestion
    │   └── ingest_documents.py
    │
    ├── tests
    │   ├── test_api.py
    │   └── test_chat_flow.py
    │
    ├── docs
    ├── logs
    │
    ├── config.yaml
    ├── requirements.txt
    └── README.md
```

---

# 3. Entrar na pasta da API

Abra o terminal e navegue até a pasta:

```
cd minhocao-wiki/api
```

---

# 4. Criar ambiente virtual

Ambiente virtual isola dependências Python do projeto.

### Linux / Mac

```
python3 -m venv venv
```

Ativar:

```
source venv/bin/activate
```

### Windows

```
python -m venv venv
```

Ativar:

```
venv\Scripts\activate
```

Se funcionou você verá algo assim no terminal:

```
(venv)
```

---

# 5. Instalar dependências

Instale todos os pacotes necessários:

```
pip install -r requirements.txt
```

Isso instalará bibliotecas como:

* FastAPI
* LangChain
* Pinecone
* OpenAI SDK

---

# 6. Configurar chaves da API

Abra o arquivo:

```
config.yaml
```

Preencha com suas chaves:

```
OPENAI_API_KEY: "SUA_CHAVE_OPENAI"
PINECONE_API_KEY: "SUA_CHAVE_PINECONE"
INDEX_NAME: "unb-rag"
```

---

# 7. Adicionar documentos

Coloque os PDFs que serão usados pelo RAG na pasta:

```
api/docs
```

Exemplo:

```
docs/
   regulamento.pdf
   cursos_unb.pdf
```

---

# 8. Rodar ingestão de documentos

Este passo cria **embeddings** e envia os documentos para o banco vetorial.

Execute:

```
python ingestion/ingest_documents.py
```

Pipeline executado:

```
PDFs
 ↓
Loader
 ↓
Chunking
 ↓
Embeddings
 ↓
Pinecone
```

Se tudo der certo aparecerá:

```
Indexação concluída
```

---

# 9. Iniciar a API

Execute:

```
uvicorn app.main:app --reload
```

O terminal mostrará algo como:

```
Uvicorn running on http://127.0.0.1:8000
```

A API agora está rodando.

---

# 10. Abrir interface da API

Abra no navegador:

```
http://localhost:8000/docs
```

Isso abre a documentação automática da API.

Lá você pode testar o endpoint `/chat`.

---

# 11. Fluxo manual com autenticação

1. Criar conta:

```
POST /auth/register
{
 "email": "usuario1@email.com",
 "password": "123456"
}
```

2. Fazer login e obter token:

```
POST /auth/login
{
 "email": "usuario1@email.com",
 "password": "123456"
}
```

No Swagger (`/docs`), o botao `Authorize` usa o endpoint padrao OAuth2:

```
POST /auth/token
Content-Type: application/x-www-form-urlencoded
username=<email>
password=<senha>
```

3. Criar conversa:

```
POST /conversations
Authorization: Bearer <TOKEN>
{
 "title": "Minha conversa"
}
```

4. Enviar pergunta no chat:

Endpoint:

```
POST /chat
```

Exemplo de body:

```
{
 "conversation_id": "<ID_DA_CONVERSA>",
 "question": "Quais cursos existem na UnB?"
}
```

Header obrigatório:

```
Authorization: Bearer <TOKEN>
```

Resposta esperada:

```
A Universidade de Brasília oferece diversos cursos de graduação...

Fonte:
cursos_unb.pdf
regulamento.pdf
```

---

# 12. Testar via script

Executar teste simples:

```
python tests/test_api.py
```

Teste de conversa:

```
python tests/test_chat_flow.py
```

Exemplo de saída:

```
Pergunta: Quais cursos existem na UnB?
Resposta: ...
```

---

# 13. Logs gerados

As consultas ficam registradas em:

```
logs/rag_logs.jsonl
```

Exemplo:

```
{
 "timestamp": "...",
 "question": "Quais cursos existem?",
 "sources": ["cursos_unb.pdf"],
 "answer": "..."
}
```

Esses logs podem ser usados para:

* análise de desempenho
* avaliação de RAG
* geração de gráficos para o TCC

---

# 14. Fluxo da arquitetura

```
Usuário
   ↓
POST /chat
   ↓
Histórico da conversa
   ↓
Qu
```
