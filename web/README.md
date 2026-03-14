# RAG Chat

Interface de chat para aplicações RAG (Retrieval-Augmented Generation) com controle de parâmetros do LLM.

## Requisitos

- Node.js 18.x ou superior
- npm, yarn ou pnpm (gerenciador de pacotes)

## Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd rag-chat
```

2. Instale as dependências:

```bash
# npm
npm install

# yarn
yarn install

# pnpm
pnpm install
```

3. Configure as variáveis de ambiente:

```bash
cp .env.example .env.local
```

Variável disponível:

```bash
API_BASE_URL=http://localhost:8000
```

Essa URL é usada pela rota interna do Next em `POST /api/chat`, que faz proxy para o backend Python em `/chat`.

## Executando o projeto

### Desenvolvimento

```bash
# npm
npm run dev

# yarn
yarn dev

# pnpm
pnpm dev
```

O servidor será iniciado em [http://localhost:3000](http://localhost:3000).

Se você alterar o arquivo `.env.local` com o servidor de desenvolvimento já rodando, reinicie o processo do Next para garantir que a nova variável seja carregada.

### Build de produção

```bash
# npm
npm run build
npm start

# yarn
yarn build
yarn start

# pnpm
pnpm build
pnpm start
```

## Estrutura do projeto

```
├── app/
│   ├── globals.css      # Estilos globais e tokens de design
│   ├── layout.tsx       # Layout principal com providers
│   └── page.tsx         # Página principal
├── components/
│   ├── ui/              # Componentes base (shadcn/ui)
│   ├── chat-interface.tsx    # Interface principal do chat
│   ├── chat-sidebar.tsx      # Sidebar com histórico
│   ├── chat-message.tsx      # Componente de mensagem
│   ├── chat-input.tsx        # Input de mensagem
│   ├── parameters-panel.tsx  # Painel de parâmetros do LLM
│   ├── parameter-control.tsx # Controle individual de parâmetro
│   ├── theme-toggle.tsx      # Botão de alternância de tema
│   └── theme-provider.tsx    # Provider de tema
└── lib/
    └── utils.ts         # Utilitários
```

## Funcionalidades

- Chat com histórico de conversas
- Sidebar ocultável com lista de conversas
- Alternância de tema (claro/escuro)
- Controle de parâmetros do LLM:
  - `temperature` - Controla a aleatoriedade das respostas
  - `max_tokens` - Limite de tokens na resposta
  - `frequency_penalty` - Penaliza palavras frequentes
  - `presence_penalty` - Penaliza palavras já mencionadas
  - `n` - Número de respostas alternativas
  - `seed` - Valor para resultados reproduzíveis
  - `stop` - Palavras que interrompem a geração

## Tecnologias

- [Next.js 15](https://nextjs.org/) - Framework React
- [Tailwind CSS](https://tailwindcss.com/) - Estilização
- [shadcn/ui](https://ui.shadcn.com/) - Componentes de UI
- [next-themes](https://github.com/pacocoursey/next-themes) - Gerenciamento de tema
- [Lucide React](https://lucide.dev/) - Ícones
