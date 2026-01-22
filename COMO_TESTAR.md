# Como Testar o Sistema após Ingestão

## Pré-requisitos

1. ✅ Ingestão concluída: `python scripts/ingest_regras_exemplo.py`
2. ✅ API rodando: `uvicorn src.agent.api:app --reload` (ou via Docker)
3. ✅ Qdrant rodando (via Docker Compose)

## Formas de Testar

### 1. Usando cURL

```bash
# Teste 1: Faturamento com valor alto (deve acionar HITL)
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d @test_1_faturamento_alto.json

# Teste 2: Faturamento com valor baixo (deve ser auto)
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d @test_2_faturamento_baixo.json

# Teste 3: Planos e Cobertura
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d @test_3_planos_cobertura.json
```

### 2. Usando Python

```python
import requests
import json

# Carregar um dos arquivos de teste
with open('test_1_faturamento_alto.json', 'r') as f:
    data = json.load(f)

# Fazer requisição
response = requests.post(
    'http://localhost:8000/agent/invoke',
    json=data
)

# Ver resultado
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))

# Verificar domínio detectado
if 'result' in result:
    intent = result['result'].get('intent', 'N/A')
    print(f"\n✅ Domínio detectado: {intent}")
    
    # Verificar regras recuperadas
    if 'retrieved_rules' in result['result']:
        rules = result['result']['retrieved_rules']
        print(f"📚 Regras encontradas: {len(rules)}")
        for rule in rules:
            print(f"  - {rule.get('rule_id', 'N/A')}: {rule.get('domain', 'N/A')}")
```

### 3. Usando Postman ou Insomnia

1. Método: `POST`
2. URL: `http://localhost:8000/agent/invoke`
3. Headers: `Content-Type: application/json`
4. Body: Copie o conteúdo de um dos arquivos `test_*.json`

## O que Verificar na Resposta

### Estrutura da Resposta

```json
{
  "result": {
    "intent": "faturamento",  // ← Domínio detectado
    "entities": {...},         // ← Entidades extraídas
    "retrieved_rules": [       // ← Regras do RAG filtradas por domínio
      {
        "text": "...",
        "rule_id": "REGRA-FAT-001",
        "domain": "faturamento",  // ← Domain nos metadados
        "confidence": 0.92,
        ...
      }
    ],
    "decision": "hitl",        // ← auto, hitl, ou reject
    "final_result_dict": {...}
  },
  "status": "success",
  "thread_id": "...",
  "requires_human_decision": true  // ← true se decision = "hitl"
}
```

### Checklist de Validação

- [ ] **Domínio detectado corretamente**
  - Verificar se `result.intent` corresponde ao domínio esperado
  - Exemplo: texto sobre faturamento → `intent: "faturamento"`

- [ ] **Regras filtradas por domínio**
  - Verificar se `retrieved_rules` contém apenas regras do domínio correto
  - Verificar se `domain` está presente nos metadados de cada regra

- [ ] **Entidades extraídas**
  - Verificar se `entities` contém procedimentos, valores, planos, etc.

- [ ] **Decisão correta**
  - Valores altos → `decision: "hitl"`
  - Valores baixos → `decision: "auto"`
  - Verificar `requires_human_decision` corresponde à decisão

- [ ] **Logs de debug**
  - Verificar logs no console da API:
    - `[DEBUG Interpretation] Detecção determinística: ...`
    - `[DEBUG Knowledge] Domínio identificado: ...`
    - `[DEBUG Knowledge] Resultados filtrados por domínio: ...`

## Exemplos de Testes por Domínio

### Faturamento

```bash
# Valor alto (deve acionar HITL)
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "User: 123abc, preciso faturar procedimento 3344, valor R$ 800",
    "user_id": "123abc",
    "case_id": "CASE-2026-001"
  }'
```

**Esperado:**
- `intent: "faturamento"`
- `retrieved_rules` com `domain: "faturamento"`
- `decision: "hitl"` (valor > R$ 500)
- `requires_human_decision: true`

### Planos e Cobertura

```bash
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "O procedimento 3344 está coberto pelo plano premium?",
    "user_id": "789ghi",
    "case_id": "CASE-2026-003"
  }'
```

**Esperado:**
- `intent: "planos_e_cobertura"`
- `retrieved_rules` com `domain: "planos_e_cobertura"`
- Regras sobre cobertura de procedimentos

### Atendimento

```bash
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Preciso contestar uma fatura. Tenho uma reclamação.",
    "user_id": "111aaa",
    "case_id": "CASE-2026-004"
  }'
```

**Esperado:**
- `intent: "atendimento"`
- `retrieved_rules` com `domain: "atendimento"` (se houver regras indexadas)

## Troubleshooting

### Problema: Nenhuma regra encontrada

**Possíveis causas:**
1. Regras não foram indexadas com campo `domain`
2. Domínio detectado não corresponde ao `domain` das regras
3. Qdrant não está rodando

**Solução:**
- Verificar logs: `[DEBUG Knowledge] Encontrados X resultados`
- Verificar se regras têm `domain` nos metadados
- Reindexar regras com campo `domain`

### Problema: Domínio incorreto

**Possíveis causas:**
1. Regras determinísticas não capturaram palavras-chave
2. LLM classificou incorretamente

**Solução:**
- Verificar logs: `[DEBUG Interpretation] Detecção determinística: ...`
- Ajustar palavras-chave em `DOMAIN_RULES` se necessário

### Problema: Filtro não funciona

**Possíveis causas:**
1. Qdrant não suporta filtros (versão antiga)
2. Campo `domain` não existe nos metadados

**Solução:**
- Verificar logs: `[WARNING Qdrant] Erro ao buscar com filtro: ...`
- Sistema deve fazer fallback para busca sem filtro
- Verificar se regras têm `domain` nos metadados

## Próximos Passos

1. ✅ Testar todos os domínios
2. ✅ Validar filtragem por domínio
3. ✅ Verificar decisões (auto/hitl)
4. ⏭️ Testar fluxo completo com HITL
5. ⏭️ Monitorar performance e precisão
