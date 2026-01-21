# Como Testar o HITL (Human-in-the-Loop)

Este guia explica como testar o fluxo completo de HITL, incluindo como responder aos interrupts.

## Fluxo Completo de Teste

### Passo 1: Criar um caso que aciona HITL

```bash
curl -X POST http://localhost:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "User: 123abc, Histórico: fez o procedimento 3344, procedimento 5566, valor total R$ 1500",
    "user_id": "123abc",
    "case_id": "CASE-2026-001"
  }'
```

**Resposta esperada:**
```json
{
  "result": {...},
  "status": "success",
  "thread_id": "abc-123-def-456",
  "requires_human_decision": true,
  "interrupt_info": {
    "interrupt_id": "b9064f1c911f72dd8b0866352403ec1a",
    ...
  }
}
```

**Importante:** Anote o `thread_id` e o `interrupt_id` da resposta!

### Passo 2: Verificar estado do thread (opcional, para debug)

```bash
THREAD_ID="abc-123-def-456"

curl http://localhost:8000/agent/thread/$THREAD_ID/state
```

**Verificar:**
- `has_interrupt: true`
- `decision: "hitl"`
- `human_decision: null`
- `interrupt_info` presente

### Passo 3: Responder ao HITL

```bash
curl -X POST http://localhost:8000/agent/hitl/decide \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "abc-123-def-456",
    "approved": true,
    "notes": "Aprovado após revisão das regras"
  }'
```

**Resposta esperada:**
```json
{
  "result": {
    "human_decision": true,
    "human_notes": "Aprovado após revisão das regras",
    "final_result": "Aprovado e processado",
    "final_result_dict": {
      "deve_ser_faturado": true,
      "source_of_truth": ["Politica_Faturamento_2024.txt"],
      ...
    }
  },
  "status": "success",
  "thread_id": "abc-123-def-456",
  "requires_human_decision": false
}
```

## Troubleshooting

### Erro: "Não há interrupt pendente para este thread"

**Possíveis causas:**

1. **Thread já foi processado**: O interrupt já foi respondido anteriormente
   - **Solução**: Use um novo `thread_id` ou verifique se já foi processado

2. **Thread não existe**: O `thread_id` está incorreto
   - **Solução**: Verifique o `thread_id` na resposta do `/invoke`

3. **Estado não foi salvo no checkpoint**: Problema com Postgres
   - **Solução**: Verifique se o Postgres está rodando e conectado

**Como debugar:**

```bash
# 1. Verificar estado do thread
curl http://localhost:8000/agent/thread/SEU_THREAD_ID/state

# 2. Verificar se Postgres está rodando
docker-compose ps db

# 3. Verificar logs da API
docker-compose logs langgraph-api
```

### Erro: "Thread não encontrado"

- Verifique se o `thread_id` está correto
- Verifique se o Postgres está rodando e a conexão está OK
- Verifique se o checkpoint está funcionando

### O interrupt não aparece

**Verificar:**

1. O caso realmente aciona HITL? (valor > threshold)
2. O grafo foi executado até o nó `hitl`?
3. O checkpoint está salvando o estado?

**Debug:**

```bash
# Ver estado completo do thread
curl http://localhost:8000/agent/thread/SEU_THREAD_ID/state

# Verificar se decision é "hitl"
# Verificar se human_decision é null
# Verificar se há interrupt_info
```

## Exemplo Completo de Teste

```bash
# 1. Criar caso que aciona HITL
RESPONSE=$(curl -s -X POST http://localhost:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "User: 123abc, Histórico: fez o procedimento 3344, procedimento 5566, valor total R$ 1500",
    "user_id": "123abc",
    "case_id": "CASE-2026-001"
  }')

# 2. Extrair thread_id (requer jq ou processamento manual)
THREAD_ID=$(echo $RESPONSE | jq -r '.thread_id')
echo "Thread ID: $THREAD_ID"

# 3. Verificar estado
curl http://localhost:8000/agent/thread/$THREAD_ID/state

# 4. Responder ao HITL
curl -X POST http://localhost:8000/agent/hitl/decide \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"approved\": true,
    \"notes\": \"Aprovado após revisão\"
  }"
```

## Formato da Requisição HITL

```json
{
  "thread_id": "string",           // OBRIGATÓRIO: ID do thread do /invoke
  "approved": true,                // OBRIGATÓRIO: true ou false
  "interrupt_id": "string",        // OPCIONAL: ID específico do interrupt
  "notes": "string"                // OPCIONAL: Observações do humano
}
```

## Respostas Possíveis

### Sucesso - Decisão processada

```json
{
  "result": {
    "human_decision": true,
    "final_result": "Aprovado e processado",
    "final_result_dict": {...}
  },
  "status": "success",
  "requires_human_decision": false
}
```

### Erro - Não há interrupt pendente

```json
{
  "detail": "Não há interrupt pendente para este thread. Debug: {...}"
}
```

O campo `debug` na mensagem de erro contém informações úteis para diagnosticar o problema.

## Dicas

1. **Sempre use o `thread_id` da resposta do `/invoke`**
2. **Não reutilize `thread_id` após responder ao HITL**
3. **Verifique o estado do thread antes de responder** se tiver dúvidas
4. **Use `notes` para adicionar observações** que serão salvas no `human_notes`
