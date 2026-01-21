# Guia: Como Rodar o Projeto com LangGraph Dev

Este documento explica como configurar e executar o projeto usando `langgraph dev` para desenvolvimento e teste visual dos grafos.

## 📋 Pré-requisitos

1. **Python 3.10 ou superior** instalado
2. **LangGraph CLI** instalado com suporte in-memory
3. **Variáveis de ambiente** configuradas (arquivo `.env`)

## 🔧 Instalação

### 1. Instalar Dependências

```bash
# Instalar o projeto e suas dependências
pip install -e .

# Instalar o LangGraph CLI com suporte in-memory (necessário para langgraph dev)
pip install "langgraph-cli[inmem]"
```

**Nota:** O projeto já inclui `langgraph-cli[inmem]>=0.4.7` no grupo de dependências `dev` do `pyproject.toml`.

### 2. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`:

```env
# OpenAI API Key (obrigatório para os grafos funcionarem)
OPENAI_API_KEY=sk-...

# LangSmith API Key (opcional, para tracing e monitoramento)
LANGSMITH_API_KEY=lsv2...

# Projeto LangSmith (opcional)
LANGSMITH_PROJECT=new-agent

# PostgreSQL URL (opcional para langgraph dev, mas necessário para a API FastAPI)
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

**Importante:** 
- Para `langgraph dev`, apenas `OPENAI_API_KEY` é obrigatório
- O `langgraph dev` usa checkpoint in-memory por padrão, então `POSTGRES_URL` não é necessário para desenvolvimento básico
- Se você quiser usar PostgreSQL com `langgraph dev`, você precisará configurar o checkpointer no código do grafo

## 🚀 Como Rodar

### Opção 1: Comando Simples

```bash
langgraph dev
```

Este comando irá:
- Iniciar o servidor LangGraph na porta padrão (geralmente 8123)
- Abrir automaticamente o LangGraph Studio no navegador
- Habilitar hot-reload automático quando você modificar o código

### Opção 2: Com Configuração de Encoding (Windows)

Se você encontrar problemas de encoding no Windows:

```powershell
$env:PYTHONIOENCODING="utf-8"
langgraph dev
```

### Opção 3: Especificando Porta e Host

```bash
langgraph dev --port 8123 --host 0.0.0.0
```

## 📊 Grafos Disponíveis

O projeto possui 3 grafos configurados no `langgraph.json`:

1. **`agent`** - Grafo principal do agente (`./src/agent/graph/graph.py:graph`)
   - Fluxo completo: interpretação → conhecimento → decisão → HITL → finalização
   - Estado: `WorkflowState` com campos como `input_text`, `intent`, `entities`, etc.

2. **`hello`** - Grafo simples de chat (`./src/agent/hello.py:graph`)
   - Chat básico com OpenAI
   - Usa `MessageGraph` para conversação

3. **`pedido_approval`** - Grafo de aprovação de pedidos (`./src/agent/pedido_approval.py:graph`)
   - Processa e-mails de pedidos
   - Inclui HITL para aprovação de pedidos acima de U$ 500

## 🎯 Usando o LangGraph Studio

Após executar `langgraph dev`, o LangGraph Studio será aberto no navegador. Você pode:

1. **Visualizar o grafo**: Ver a estrutura completa do grafo com todos os nós e arestas
2. **Testar o grafo**: Enviar inputs e ver a execução em tempo real
3. **Debugar**: Editar estados anteriores e reexecutar a partir de qualquer ponto
4. **Inspecionar estados**: Ver o estado em cada nó durante a execução
5. **Testar HITL**: Interagir com interrupts (Human-in-the-Loop) diretamente na interface

### Exemplo de Input para o Grafo `agent`:

```json
{
  "input_text": "Preciso fazer um pedido de compra no valor de R$ 1200,00"
}
```

### Exemplo de Input para o Grafo `pedido_approval`:

```json
{
  "email_content": "Assunto: Pedido de Compra #ORD-001\n\nPrezado Gerente,\n\nSolicitamos aprovação para o seguinte pedido:\n\nID do Pedido: ORD-001\nDescrição: Equipamentos de escritório\nValor: U$ 750.00\n\nPor favor, analise e aprove se necessário."
}
```

## 🔍 Diferenças entre `langgraph dev` e a API FastAPI

| Aspecto | `langgraph dev` | API FastAPI (`api.py`) |
|---------|----------------|------------------------|
| **Checkpoint** | In-memory (padrão) | PostgreSQL |
| **Interface** | LangGraph Studio (web) | REST API |
| **Uso** | Desenvolvimento e debug | Produção |
| **Hot Reload** | Automático | Manual (com `--reload`) |
| **HITL** | Interface visual integrada | Endpoints REST (`/agent/hitl/decide`) |

## ⚠️ Troubleshooting

### Problema: "ModuleNotFoundError" ou imports não funcionam

**Solução:** Certifique-se de que instalou o projeto em modo editável:
```bash
pip install -e .
```

### Problema: "OPENAI_API_KEY not found"

**Solução:** Verifique se o arquivo `.env` existe e contém a chave:
```bash
# Windows PowerShell
Get-Content .env | Select-String "OPENAI_API_KEY"

# Linux/Mac
grep OPENAI_API_KEY .env
```

### Problema: Porta já em uso

**Solução:** Use uma porta diferente:
```bash
langgraph dev --port 8124
```

### Problema: Grafo não aparece no Studio

**Solução:** Verifique se o `langgraph.json` está correto e os caminhos dos grafos estão corretos:
```json
{
  "graphs": {
    "agent": "./src/agent/graph/graph.py:graph",
    "hello": "./src/agent/hello.py:graph",
    "pedido_approval": "./src/agent/pedido_approval.py:graph"
  }
}
```

### Problema: Erro ao executar grafo com HITL

**Solução:** O `langgraph dev` suporta interrupts nativamente. Certifique-se de que o grafo está usando `interrupt()` corretamente. No Studio, você verá uma interface para responder aos interrupts.

### Problema: Encoding no Windows

**Solução:** Configure a variável de ambiente antes de rodar:
```powershell
$env:PYTHONIOENCODING="utf-8"
langgraph dev
```

## 📚 Recursos Adicionais

- [Documentação LangGraph](https://langchain-ai.github.io/langgraph/)
- [LangGraph Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/)
- [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/)
- [LangGraph CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/)

## 🔄 Próximos Passos

1. **Modificar os grafos**: Edite os arquivos em `src/agent/graph/` ou `src/agent/`
2. **Adicionar novos nós**: Crie novos nós em `src/agent/graph/nodes/`
3. **Testar mudanças**: O hot-reload do `langgraph dev` aplicará mudanças automaticamente
4. **Visualizar execução**: Use o Studio para entender o fluxo de dados
5. **Debugar problemas**: Use a funcionalidade de editar estado e reexecutar no Studio

## 💡 Dicas

- Use o LangGraph Studio para entender melhor como os dados fluem entre os nós
- O hot-reload funciona para mudanças em nós e estrutura do grafo
- Você pode criar novos threads no Studio usando o botão `+` no canto superior direito
- O Studio permite editar estados anteriores e reexecutar a partir de qualquer ponto, útil para debug
- Para produção, use a API FastAPI (`api.py`) que suporta PostgreSQL checkpoint e endpoints REST
