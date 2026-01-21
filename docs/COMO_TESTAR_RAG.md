# Como Testar o Sistema RAG - Guia Passo a Passo

Este guia explica como testar a implementação do RAG passo a passo.

## Pré-requisitos

1. **Qdrant rodando**: O banco vetorial precisa estar ativo
2. **Variáveis de ambiente**: `OPENAI_API_KEY` configurada
3. **Python**: Ambiente com dependências instaladas

## Passo 1: Verificar se o Qdrant está rodando

```bash
# Verificar se o container está ativo
docker-compose ps qdrant

# Se não estiver rodando, iniciar:
docker-compose up -d qdrant

# Verificar logs (opcional):
docker-compose logs qdrant
```

## Passo 2: Preparar arquivos de regras (já criados)

Os arquivos de exemplo já foram criados em `docs_regras/`:

- `Politica_Faturamento_2024.txt` - Políticas de faturamento
- `Contrato_Operadora_XYZ.txt` - Termos do contrato

Você pode criar seus próprios arquivos seguindo o formato:

```
SEÇÃO: Nome da Seção

REGRA-ID: Descrição da regra aqui. Pode ter múltiplas linhas.
```

## Passo 3: Indexar regras no Qdrant

**IMPORTANTE**: Se você está rodando a API via Docker Compose, precisa indexar as regras no Qdrant do Docker, não no localhost!

### Opção A: Indexar no Qdrant do Docker (Recomendado se usando Docker)

Se a API está rodando via `docker-compose up -d`, use este script:

```bash
# Rodar dentro do container Docker (usa Qdrant do Docker)
docker-compose exec langgraph-api python scripts/ingest_regras_docker.py

# OU rodar localmente apontando para Qdrant do Docker
QDRANT_HOST=localhost QDRANT_PORT=6333 python scripts/ingest_regras_docker.py
```

### Opção B: Indexar no Qdrant local (se API rodando localmente)

Se a API está rodando localmente (não via Docker), use:

```bash
# Na raiz do projeto
python scripts/ingest_regras_exemplo.py
```

**O que o script faz:**
- Indexa 8 regras diferentes com metadados completos
- Inclui regras de faturamento, cobertura e auditoria
- Cada regra tem metadados: `source`, `section`, `rule_id`, `page`, `line_range`, `tipo_regra`, etc.

### Opção B: Indexar manualmente via Python

```python
import sys
sys.path.insert(0, "src")

from agent.rag.ingest import ingest_text_with_metadata

# Exemplo de regra
texto = """
Procedimentos com valor acima de R$ 500,00 requerem aprovação humana.
"""

metadata = {
    "source": "Politica_Faturamento_2024.txt",
    "section": "Aprovação de Faturamento",
    "rule_id": "REGRA-FAT-001",
    "page": "1",
    "line_range": "5-6",
    "tipo_regra": "faturamento",
    "updated_at": "2024-01-15T10:00:00Z",
    "valid_from": "2024-01-01T00:00:00Z",
    "departamento": "Faturamento"
}

ingest_text_with_metadata(texto.strip(), metadata)
```

### Opção C: Indexar arquivo completo (sem metadados detalhados)

```python
from agent.rag.ingest import ingest_text

# Indexa texto simples (só com source)
ingest_text(
    "Procedimentos acima de R$ 500 requerem aprovação.",
    source="Minha_Regra.txt"
)
```

## Passo 4: Verificar se as regras foram indexadas

Você pode verificar de algumas formas:

### Via API do Qdrant (opcional)

```bash
# Listar coleções
curl http://localhost:6333/collections

# Ver informações da coleção
curl http://localhost:6333/collections/empresa_m_regras
```

### Via código Python

```python
from agent.rag.qdrant import _get_vector_store

# Buscar algumas regras
results = _get_vector_store().similarity_search("aprovação faturamento", k=3)

for doc in results:
    print(f"Texto: {doc.page_content[:100]}...")
    print(f"Metadados: {doc.metadata}")
    print("---")
```

## Passo 5: Testar o fluxo completo via API

### 5.1. Iniciar a API

```bash
# Em um terminal
python -m uvicorn agent.api:app --reload --port 8000
```

### 5.2. Testar com caso de exemplo

**Caso 1: Valor acima de R$ 500 (deve acionar HITL)**

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
  "result": {
    "decision": "hitl",
    "retrieved_rules": [
      {
        "text": "Procedimentos com valor acima de R$ 500,00 requerem aprovação...",
        "source": "Politica_Faturamento_2024.txt",
        "rule_id": "REGRA-FAT-001",
        "confidence": 0.92
      }
    ],
    "decision_reasoning": "Valor de R$ 1500 acima do threshold de R$ 500...",
    "requires_human_decision": true
  }
}
```

**Caso 2: Valor abaixo de R$ 500 (deve ser automático)**

```bash
curl -X POST http://localhost:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "User: 456def, Histórico: fez o procedimento 3344, valor total R$ 300",
    "user_id": "456def",
    "case_id": "CASE-2026-002"
  }'
```

**Resposta esperada:**
```json
{
  "result": {
    "decision": "auto",
    "final_result": "Aprovado e processado",
    "final_result_dict": {
      "deve_ser_faturado": true,
      "source_of_truth": ["Politica_Faturamento_2024.txt"]
    }
  }
}
```

## Passo 6: Verificar estado do grafo (se HITL)

Se a decisão for `hitl`, você pode verificar o estado completo:

```bash
# Obter thread_id da resposta anterior
THREAD_ID="abc-123-def-456"

curl http://localhost:8000/agent/thread/$THREAD_ID/state
```

**Resposta esperada:**
```json
{
  "state": {
    "retrieved_rules": [
      {
        "text": "...",
        "source": "Politica_Faturamento_2024.txt",
        "rule_id": "REGRA-FAT-001",
        "section": "Aprovação de Faturamento",
        "confidence": 0.92
      }
    ],
    "decision": "hitl",
    "decision_evidence": ["REGRA-FAT-001"],
    "decision_reasoning": "...",
    "has_interrupt": true,
    "interrupt_info": {
      "question": "Deve ser faturado o caso CASE-2026-001...",
      "fatos": {...},
      "regras_aplicadas": [...],
      "source_of_truth": ["Politica_Faturamento_2024.txt"]
    }
  }
}
```

## Passo 7: Responder ao HITL (se necessário)

Se houver interrupt, você precisa responder:

```bash
curl -X POST http://localhost:8000/agent/human-decision \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "abc-123-def-456",
    "approved": true,
    "notes": "Aprovado após revisão das regras"
  }'
```

## Exemplos de Input para Testar

### Exemplo 1: Caso com múltiplos procedimentos
```json
{
  "input_text": "User: 789ghi, Histórico: fez procedimento 3344 (Consulta Cardiológica), procedimento 5566 (Exame de Sangue), medicações A e B, valor total R$ 1200, plano premium",
  "user_id": "789ghi",
  "case_id": "CASE-2026-003"
}
```

### Exemplo 2: Caso de urgência
```json
{
  "input_text": "User: 111jkl, Histórico: procedimento de urgência código 9999, valor R$ 2000, plano básico",
  "user_id": "111jkl",
  "case_id": "CASE-2026-004"
}
```

### Exemplo 3: Caso abaixo do limite
```json
{
  "input_text": "User: 222mno, Histórico: procedimento 3344, valor R$ 200",
  "user_id": "222mno",
  "case_id": "CASE-2026-005"
}
```

## Troubleshooting

### Erro: "Connection refused" ao conectar no Qdrant

```bash
# Verificar se Qdrant está rodando
docker-compose ps qdrant

# Se não estiver, iniciar
docker-compose up -d qdrant

# Verificar variáveis de ambiente
echo $QDRANT_HOST  # Deve ser "localhost" ou "qdrant"
echo $QDRANT_PORT  # Deve ser "6333"
```

### Erro: "No module named 'agent'"

Certifique-se de estar na raiz do projeto e que o Python consegue encontrar o módulo:

```bash
# Verificar estrutura
ls src/agent/rag/

# Executar script da raiz
python scripts/ingest_regras_exemplo.py
```

### Nenhuma regra encontrada na busca

1. Verifique se as regras foram indexadas:
   ```python
   from agent.rag.qdrant import _get_vector_store
   results = _get_vector_store().similarity_search("aprovação", k=5)
   print(f"Encontrados {len(results)} resultados")
   ```

2. Verifique se a query está sendo construída corretamente (veja logs do nó `knowledge`)

3. Tente uma busca mais genérica primeiro

## Próximos Passos

Após testar com sucesso:

1. **Adicionar mais regras**: Crie seus próprios documentos de regras
2. **Melhorar Interpret**: Use LLM com estrutura de saída (Pydantic)
3. **Adicionar filtros**: Filtre regras por `tipo_regra` ou `valid_from`
4. **Implementar auditoria**: Crie tabela no Postgres para rastrear decisões

## Estrutura de Arquivos Criados

```
docs_regras/
├── Politica_Faturamento_2024.txt    # Regras de faturamento
└── Contrato_Operadora_XYZ.txt       # Termos do contrato

scripts/
└── ingest_regras_exemplo.py        # Script para indexar regras

docs/
├── COMO_TESTAR_RAG.md              # Este guia
├── exemplo_regras_metadados.md      # Guia de metadados
└── FLUXO_RAG_IMPLEMENTACAO.md      # Fluxo completo
```
