# Fluxo de Informação - Sistema RAG de Governança

Este documento explica o fluxo completo de informação no sistema de orquestração de decisão com governança para planos de saúde.

## Visão Geral do Fluxo

```
INPUT → Interpret → Knowledge (RAG) → Decision → HITL → Finalize → OUTPUT
```

## Detalhamento de Cada Etapa

### 1. **INPUT** - Entrada do Sistema

**Formato de Entrada:**
```json
{
  "input_text": "User: 123abc, Histórico: fez o procedimento 3344, procedimento 5566, medicações A e B",
  "user_id": "123abc",
  "case_id": "CASE-2026-001"
}
```

**Onde:** Endpoint `/agent/invoke` (API FastAPI)

**Estado Inicial Criado:**
```python
WorkflowState = {
    "input_text": "...",
    "user_id": "123abc",
    "case_id": "CASE-2026-001",
    "intent": "",
    "entities": {},
    "retrieved_context": "",
    "retrieved_rules": None,
    "decision": "auto",
    "decision_evidence": None,
    "decision_reasoning": None,
    "human_decision": None,
    "human_notes": None,
    "final_result": "",
    "final_result_dict": None
}
```

---

### 2. **NODE: Interpret** - Extração de Intenção e Entidades

**Arquivo:** `src/agent/graph/nodes/interpretation.py`

**Responsabilidade:**
- Analisa o texto de entrada usando LLM
- Extrai **intenção** (ex: "pode_faturar", "quem_paga", "precisa_auditoria")
- Extrai **entidades** estruturadas (procedimentos, valores, plano, etc.)

**Processamento:**
```python
# LLM analisa o texto
response = llm.invoke(f"Analise o texto e retorne intenção e entidades:\n{input_text}")

# Retorna:
{
    "intent": "pode_faturar",
    "entities": {
        "procedimentos": ["3344", "5566"],
        "medicacoes": ["A", "B"],
        "valor_total": 1500.00,
        "plano": "premium",
        "localidade": "SP"
    }
}
```

**Estado Após Interpret:**
```python
{
    "intent": "pode_faturar",  # ← Preenchido
    "entities": {...},          # ← Preenchido
    # ... resto do estado
}
```

---

### 3. **NODE: Knowledge** - Busca RAG de Regras

**Arquivo:** `src/agent/graph/nodes/knowledge.py`

**Responsabilidade:**
- Constrói query semântica a partir de `intent` + `entities`
- Busca regras relevantes no Qdrant usando embeddings
- Retorna regras estruturadas com metadados completos

**Processamento:**

**Passo 3.1: Construção da Query**
```python
# Query construída automaticamente:
query = """
Intenção: pode_faturar
Contexto: 
- Procedimentos: 3344, 5566
- Valor: R$ 1500
- Plano: premium
"""
```

**Passo 3.2: Busca no Qdrant**
```python
# Chama função em qdrant.py
results = search_docs_with_metadata(query, k=5)

# Retorna lista de Document com:
# - page_content: texto da regra
# - metadata: {source, section, rule_id, page, line_range, score, ...}
```

**Passo 3.3: Formatação de Regras**
```python
retrieved_rules = [
    {
        "text": "Procedimentos com valor acima de R$ 500,00 requerem aprovação...",
        "source": "Politica_Faturamento_2024.docx",
        "section": "Aprovação de Faturamento",
        "rule_id": "REGRA-FAT-001",
        "page": "12",
        "line_range": "89-90",
        "confidence": 0.92,  # Score de relevância
        "tipo_regra": "faturamento"
    },
    # ... mais regras
]
```

**Estado Após Knowledge:**
```python
{
    "retrieved_context": "[Politica_Faturamento_2024.docx] Procedimentos com valor...",  # ← Texto concatenado
    "retrieved_rules": [...],  # ← Lista estruturada com metadados
    # ... resto do estado
}
```

---

### 4. **NODE: Decision** - Aplicação de Regras e Decisão

**Arquivo:** `src/agent/graph/nodes/decision.py`

**Responsabilidade:**
- Analisa regras recuperadas vs entidades do caso
- Extrai thresholds e condições das regras
- Decide se requer aprovação humana (HITL) ou pode ser automático
- Prepara evidências e raciocínio da decisão

**Processamento:**

**Passo 4.1: Análise de Regras**
```python
# Filtra regras com alta confiança (> 0.7)
high_confidence_rules = [r for r in retrieved_rules if r["confidence"] > 0.7]

# Extrai threshold das regras (ex: "acima de R$ 500")
# Busca padrões como "acima de R$", "maior que", etc.
threshold = 500  # Extraído das regras
```

**Passo 4.2: Decisão**
```python
valor_total = entities.get("valor_total", 0)

if valor_total > threshold:
    decision = "hitl"
    decision_reasoning = "Valor de R$ 1500 acima do threshold de R$ 500 conforme regras..."
    decision_evidence = ["REGRA-FAT-001", "REGRA-FAT-002"]
else:
    decision = "auto"
    decision_reasoning = "Valor dentro do limite para aprovação automática"
```

**Estado Após Decision:**
```python
{
    "decision": "hitl",  # ← "auto", "hitl" ou "reject"
    "decision_evidence": ["REGRA-FAT-001"],  # ← IDs das regras usadas
    "decision_reasoning": "Valor de R$ 1500 acima do threshold...",  # ← Explicação
    # ... resto do estado
}
```

---

### 5. **NODE: HITL** - Aprovação Humana (se necessário)

**Arquivo:** `src/agent/graph/nodes/hitl.py`

**Responsabilidade:**
- Apresenta informações estruturadas ao humano
- Inclui fatos, regras aplicadas, evidências e rastreabilidade
- Aguarda decisão humana via interrupt
- Captura observações do humano

**Processamento:**

**Passo 5.1: Preparação da Apresentação**
```python
presentation = {
    "user_id": "123abc",
    "case_id": "CASE-2026-001",
    "question": "Deve ser faturado o caso CASE-2026-001 para o usuário 123abc?",
    
    # Fatos estruturados
    "fatos": {
        "procedimentos": ["3344", "5566"],
        "valor_total": 1500.00,
        "plano": "premium",
        "medicacoes": ["A", "B"],
        "localidade": "SP"
    },
    
    # Regras aplicadas (com metadados)
    "regras_aplicadas": [
        {
            "regra": "Procedimentos com valor acima de R$ 500,00 requerem aprovação...",
            "fonte": "Politica_Faturamento_2024.docx",
            "secao": "Aprovação de Faturamento",
            "linhas": "89-90",
            "confianca": 0.92,
            "rule_id": "REGRA-FAT-001"
        }
    ],
    
    # Rastreabilidade (Source of Truth)
    "source_of_truth": [
        "Politica_Faturamento_2024.docx",
        "Contrato_Operadora_XYZ.pdf"
    ],
    
    # Razão da decisão sugerida
    "razao": "Valor de R$ 1500 acima do threshold de R$ 500 conforme regras recuperadas",
    
    # Sugestão inicial
    "sugestao": "Sim"
}
```

**Passo 5.2: Interrupt e Resposta Humana**
```python
# Interrupt pausa execução e mostra apresentação ao humano
decision = interrupt(presentation)

# Humano responde:
{
    "approved": True,
    "notes": "Aprovado após revisão das regras"
}
```

**Estado Após HITL:**
```python
{
    "human_decision": True,  # ← Decisão do humano
    "human_notes": "Aprovado após revisão das regras",  # ← Observações
    # ... resto do estado
}
```

---

### 6. **NODE: Finalize** - Resultado Final Estruturado

**Arquivo:** `src/agent/graph/nodes/finalize.py`

**Responsabilidade:**
- Consolida todas as informações
- Gera resultado final estruturado
- Inclui rastreabilidade completa (Source of Truth)
- Prepara resposta para o cliente

**Processamento:**
```python
# Determina resultado baseado em human_decision
if human_decision is False:
    deve_ser_faturado = False
    resultado_texto = "Rejeitado"
else:
    deve_ser_faturado = True
    resultado_texto = "Aprovado e processado"

# Extrai Source of Truth das regras
source_of_truth = [
    "Politica_Faturamento_2024.docx",
    "Contrato_Operadora_XYZ.pdf"
]

# Constrói resultado estruturado
final_result_dict = {
    "deve_ser_faturado": True,
    "quem_paga": "operadora",
    "precisa_auditoria": True,
    "source_of_truth": source_of_truth,
    "razao": "Valor de R$ 1500 acima do threshold... | Observações: Aprovado após revisão",
    "decision_evidence": ["REGRA-FAT-001"],
    "user_id": "123abc",
    "case_id": "CASE-2026-001"
}
```

**Estado Final:**
```python
{
    "final_result": "Aprovado e processado",  # ← Texto legível
    "final_result_dict": {...},  # ← Estrutura completa com rastreabilidade
    # ... resto do estado
}
```

---

## Fluxo de Dados Visual

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT                                                           │
│ input_text: "User: 123abc, Histórico: procedimento 3344..."   │
│ user_id: "123abc"                                               │
│ case_id: "CASE-2026-001"                                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE: Interpret                                                 │
│ • Extrai intent: "pode_faturar"                                 │
│ • Extrai entities: {procedimentos: [...], valor_total: 1500}    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE: Knowledge (RAG)                                           │
│ • Query: "Intenção: pode_faturar, Procedimentos: 3344, 5566..." │
│ • Busca no Qdrant → retrieved_rules: [...]                     │
│   - source: "Politica_Faturamento_2024.docx"                    │
│   - rule_id: "REGRA-FAT-001"                                    │
│   - confidence: 0.92                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE: Decision                                                  │
│ • Analisa regras vs entidades                                   │
│ • Threshold extraído: R$ 500                                    │
│ • Decision: "hitl" (valor 1500 > 500)                          │
│ • Evidence: ["REGRA-FAT-001"]                                    │
│ • Reasoning: "Valor acima do threshold..."                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE: HITL (se decision == "hitl")                            │
│ • Interrupt com apresentação estruturada:                       │
│   - Fatos: {procedimentos, valor_total, plano}                  │
│   - Regras aplicadas: [{regra, fonte, linhas, confiança}]      │
│   - Source of Truth: ["Documento456.docx"]                      │
│   - Razão: "Regra XYZ linhas 89-90"                             │
│ • Aguarda decisão humana                                        │
│ • human_decision: True                                          │
│ • human_notes: "Aprovado após revisão"                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE: Finalize                                                  │
│ • Consolida informações                                         │
│ • final_result_dict: {                                          │
│     deve_ser_faturado: True,                                    │
│     source_of_truth: [...],                                     │
│     razao: "...",                                               │
│     decision_evidence: [...]                                    │
│   }                                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT                                                          │
│ {                                                               │
│   "deve_ser_faturado": true,                                    │
│   "source_of_truth": ["Politica_Faturamento_2024.docx"],        │
│   "razao": "Regra REGRA-FAT-001 aplicada...",                   │
│   "user_id": "123abc",                                          │
│   "case_id": "CASE-2026-001"                                    │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Pontos-Chave da Implementação

### 1. **Rastreabilidade Completa**
- Cada decisão rastreia quais regras foram usadas (`decision_evidence`)
- Source of Truth explícito (`source_of_truth`)
- Metadados completos em cada regra (fonte, seção, linhas, ID)

### 2. **Separação de Responsabilidades**
- **Interpret**: Extrai fatos estruturados
- **Knowledge**: Busca regras não estruturadas (RAG)
- **Decision**: Aplica regras aos fatos
- **HITL**: Apresenta evidências ao humano
- **Finalize**: Consolida e estrutura resultado

### 3. **Compatibilidade**
- Mantém campos antigos (`retrieved_context`, `final_result`) para compatibilidade
- Adiciona campos novos estruturados (`retrieved_rules`, `final_result_dict`)
- Transição gradual possível

### 4. **Governança**
- Todas as decisões têm evidências documentadas
- Regras vêm de documentos, não de código hardcoded
- Auditoria completa possível via `decision_evidence` e `source_of_truth`

## Próximos Passos Sugeridos

1. **Melhorar Interpret**: Usar LLM com estrutura de saída definida (Pydantic)
2. **Filtros no RAG**: Adicionar filtros por `tipo_regra` e `valid_from`
3. **Versionamento**: Implementar versionamento de regras
4. **Auditoria**: Criar tabela de auditoria no Postgres para rastrear decisões
5. **Ingestão**: Criar endpoint/CLI para ingestão de documentos com metadados
