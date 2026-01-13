# Deploy da API LangGraph Agent

Este documento descreve como fazer o deploy da API FastAPI que expõe o agente LangGraph.

## Pré-requisitos

- Docker instalado
- Docker Compose instalado
- Arquivo `.env` configurado com as variáveis necessárias

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# OpenAI API Key (obrigatório)
OPENAI_API_KEY=sk-...

# LangSmith API Key (opcional, para tracing)
LANGSMITH_API_KEY=lsv2...

# Configurações do Qdrant (opcional, valores padrão já configurados)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=empresa_m_regras
```

## Como Fazer o Deploy

### 1. Construir e iniciar os serviços

```bash
docker-compose up -d --build
```

Este comando irá:
- Construir a imagem Docker da API
- Iniciar o serviço Qdrant
- Iniciar o serviço da API FastAPI
- Configurar a rede entre os serviços

### 2. Verificar se os serviços estão rodando

```bash
docker-compose ps
```

Você deve ver dois serviços:
- `qdrant` - Banco de dados vetorial
- `langgraph-api` - API FastAPI

### 3. Verificar os logs

```bash
# Logs de todos os serviços
docker-compose logs -f

# Logs apenas da API
docker-compose logs -f langgraph-api

# Logs apenas do Qdrant
docker-compose logs -f qdrant
```

### 4. Testar a API

A API estará disponível em `http://localhost:8000`

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Documentação Interativa

Acesse a documentação Swagger em:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Testar o Agente

```bash
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Preciso fazer um pedido de compra no valor de R$ 600,00"
  }'
```

## Endpoints Disponíveis

### GET `/`
Health check básico

### GET `/health`
Health check detalhado

### POST `/agent/invoke`
Invoca o grafo do agente de forma síncrona

**Request Body:**
```json
{
  "input_text": "Texto de entrada para o agente",
  "config": {}  // Opcional
}
```

**Response:**
```json
{
  "result": {
    "input_text": "...",
    "intent": "...",
    "entities": {...},
    "retrieved_context": "...",
    "decision": "auto|hitl|reject",
    "human_decision": true|false|null,
    "final_result": "..."
  },
  "status": "success"
}
```

### POST `/agent/stream`
Invoca o grafo do agente com streaming de eventos

**Request Body:**
```json
{
  "input_text": "Texto de entrada para o agente",
  "config": {},  // Opcional
  "thread_id": "abc-123"  // Opcional, para continuar execução
}
```

**Response:** Stream de eventos em tempo real

### POST `/agent/hitl/decide`
Processa a decisão humana e continua a execução após um interrupt (HITL)

**Request Body:**
```json
{
  "thread_id": "abc-123",  // Obrigatório: ID do thread retornado na primeira chamada
  "approved": true,  // true para aprovar, false para rejeitar
  "interrupt_id": "f1e9fbb3..."  // Opcional: ID específico do interrupt
}
```

**Response:**
```json
{
  "result": {
    "input_text": "...",
    "intent": "...",
    "entities": {...},
    "retrieved_context": "...",
    "decision": "hitl",
    "human_decision": true,
    "final_result": "Aprovado e processado"
  },
  "status": "success",
  "thread_id": "abc-123",
  "requires_human_decision": false,
  "interrupt_info": null
}
```

### GET `/agent/thread/{thread_id}/state`
Obtém o estado atual de um thread

**Response:**
```json
{
  "thread_id": "abc-123",
  "state": {
    "input_text": "...",
    "intent": "...",
    "entities": {...},
    "retrieved_context": "...",
    "decision": "hitl",
    "human_decision": null,
    "final_result": "",
    "__interrupt__": [...]
  },
  "next": [],
  "has_interrupt": true,
  "interrupt_info": {
    "question": "Você aprova este pedido?",
    "context": "..."
  },
  "interrupt_id": "f1e9fbb3..."
}
```

## Fluxo de HITL (Human-in-the-Loop)

Quando o agente precisa de uma decisão humana, o fluxo é o seguinte:

### 1. Invocar o agente

```bash
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Pedido de compra no valor de R$ 1200,00"
  }'
```

**Resposta (quando há HITL):**
```json
{
  "result": {
    "__interrupt__": [
      {
        "value": {
          "question": "Você aprova este pedido?",
          "context": "..."
        },
        "id": "f1e9fbb3..."
      }
    ],
    ...
  },
  "status": "success",
  "thread_id": "abc-123-def-456",
  "requires_human_decision": true,
  "interrupt_info": {
    "question": "Você aprova este pedido?",
    "context": "...",
    "interrupt_id": "f1e9fbb3..."
  }
}
```

### 2. Enviar decisão humana

```bash
curl -X POST "http://localhost:8000/agent/hitl/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "abc-123-def-456",
    "approved": true
  }'
```

**Resposta:**
```json
{
  "result": {
    "input_text": "...",
    "intent": "pedido_compra",
    "entities": {"valor": 1200},
    "retrieved_context": "...",
    "decision": "hitl",
    "human_decision": true,
    "final_result": "Aprovado e processado"
  },
  "status": "success",
  "thread_id": "abc-123-def-456",
  "requires_human_decision": false,
  "interrupt_info": null
}
```

### 3. Consultar estado (opcional)

Se você quiser verificar o estado antes de decidir:

```bash
curl "http://localhost:8000/agent/thread/abc-123-def-456/state"
```

## Parar os Serviços

```bash
# Parar os serviços (mantém os dados)
docker-compose down

# Parar e remover volumes (remove todos os dados)
docker-compose down -v
```

## Reconstruir após Mudanças no Código

```bash
# Reconstruir apenas a API
docker-compose build langgraph-api

# Reiniciar o serviço
docker-compose up -d langgraph-api
```

## Desenvolvimento Local (sem Docker)

Se preferir rodar localmente sem Docker:

```bash
# Instalar dependências
pip install -e . "langgraph-cli[inmem]"

# Iniciar Qdrant (em outro terminal)
docker-compose up -d qdrant

# Configurar variáveis de ambiente
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export OPENAI_API_KEY=sk-...

# Rodar a API
uvicorn agent.api:app --host 0.0.0.0 --port 8000 --reload
```

## Troubleshooting

### Erro: "Connection refused" ao conectar no Qdrant

Verifique se o Qdrant está rodando:
```bash
docker-compose ps qdrant
```

Verifique os logs:
```bash
docker-compose logs qdrant
```

### Erro: "OPENAI_API_KEY not found"

Certifique-se de que o arquivo `.env` existe e contém a chave:
```bash
cat .env | grep OPENAI_API_KEY
```

### Porta 8000 já em uso

Altere a porta no `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use 8001 no host
```

E atualize a URL de acesso para `http://localhost:8001`

### Rebuild completo

Se houver problemas com cache do Docker:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Estrutura dos Arquivos

```
.
├── Dockerfile              # Imagem Docker da API
├── docker-compose.yml      # Orquestração dos serviços
├── .env                    # Variáveis de ambiente (não versionado)
├── src/
│   └── agent/
│       ├── api.py          # API FastAPI
│       ├── graph/
│       │   └── graph.py    # Grafo LangGraph
│       └── rag/
│           └── qdrant.py   # Cliente Qdrant
└── pyproject.toml          # Dependências do projeto
```

## Debug Remoto com VS Code

O projeto está configurado para permitir debug remoto do código rodando dentro do Docker.

### Como Usar

1. **Reconstruir o container com debugpy:**
```bash
docker-compose up -d --build
```

2. **Aguardar o container iniciar:**
O container vai aguardar a conexão do debugger antes de iniciar a API (devido ao `--wait-for-client`).

3. **Conectar o debugger no VS Code:**
   - Pressione `F5` ou vá em Run > Start Debugging
   - Selecione "Python: Debug Remoto (Docker)"
   - O debugger vai conectar e a API vai iniciar

4. **Colocar breakpoints:**
   - Abra qualquer arquivo em `src/agent/`
   - Clique na margem esquerda para adicionar breakpoints
   - Faça requisições para `http://localhost:8000`
   - O código vai pausar nos breakpoints

### Configurações Disponíveis

O arquivo `.vscode/launch.json` contém 4 configurações:

- **Python: Debug Remoto (Docker)** - Debug do código rodando no Docker
- **Python: FastAPI (Local)** - Debug local sem Docker (requer Qdrant rodando)
- **Python: Current File** - Debug do arquivo atual
- **Python: Test HITL** - Debug do script de teste HITL

### Desabilitar --wait-for-client

Se você quiser que a API inicie normalmente e conecte o debugger depois, modifique o `Dockerfile`:

```dockerfile
# Remova --wait-for-client
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Troubleshooting

**Problema: Debugger não conecta**
- Verifique se a porta 5678 está exposta: `docker-compose ps`
- Verifique os logs: `docker-compose logs langgraph-api`
- Certifique-se de que o container foi reconstruído após adicionar debugpy

**Problema: Breakpoints não funcionam**
- Verifique se os `pathMappings` estão corretos no `launch.json`
- Certifique-se de que o código local corresponde ao código no container
- Use `justMyCode: false` para debugar código de bibliotecas também

## Próximos Passos

- Configurar autenticação na API (JWT, API Keys, etc.)
- Adicionar rate limiting
- Configurar HTTPS com certificado SSL
- Implementar monitoramento e logging estruturado
- Configurar CI/CD para deploy automático
