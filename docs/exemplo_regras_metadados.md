# Exemplo de Documentos de Regras com Metadados Recomendados

Este documento descreve o formato recomendado para indexar regras no sistema RAG, incluindo os metadados necessários para rastreabilidade e governança.

## Estrutura de Metadados Recomendada

Ao indexar documentos de regras no Qdrant, cada chunk deve incluir os seguintes metadados:

### Metadados Obrigatórios

- **`source`** (string): Nome do arquivo fonte
  - Exemplo: `"Politica_Faturamento_2024.docx"`
  - Exemplo: `"Contrato_Operadora_XYZ.pdf"`

- **`section`** (string): Seção ou categoria da regra
  - Exemplo: `"Aprovação de Faturamento"`
  - Exemplo: `"Cobertura de Procedimentos"`
  - Exemplo: `"Regras de Auditoria"`

- **`rule_id`** (string): ID único da regra (para rastreabilidade)
  - Exemplo: `"REGRA-FAT-001"`
  - Exemplo: `"COBERTURA-PROC-3344"`
  - Formato recomendado: `{TIPO}-{CATEGORIA}-{NUMERO}`

### Metadados Opcionais (mas Recomendados)

- **`page`** (string ou int): Página do documento (se aplicável)
  - Exemplo: `"12"` ou `12`

- **`line_range`** (string): Intervalo de linhas onde a regra está
  - Exemplo: `"89-90"`
  - Exemplo: `"150-155"`

- **`tipo_regra`** (string): Tipo/categoria da regra
  - Valores sugeridos: `"faturamento"`, `"cobertura"`, `"auditoria"`, `"aprovacao"`
  - Facilita filtros e buscas direcionadas

- **`updated_at`** (string): Data de atualização da regra (ISO 8601)
  - Exemplo: `"2026-01-20T10:15:00Z"`
  - Útil para versionamento e auditoria

- **`valid_from`** (string): Data de vigência da regra (ISO 8601)
  - Exemplo: `"2024-01-01T00:00:00Z"`
  - Permite filtrar regras por período de vigência

- **`departamento`** (string): Departamento responsável
  - Exemplo: `"Faturamento"`
  - Exemplo: `"Cobertura"`

## Exemplo de Documento de Regra

### Documento: `Politica_Faturamento_2024.docx`

#### Seção 1: Aprovação de Faturamento

**Chunk 1:**
```
Texto: "Procedimentos com valor acima de R$ 500,00 requerem aprovação humana antes do faturamento. Esta regra se aplica a todos os planos, exceto planos premium que possuem limite de R$ 1.000,00."

Metadados:
{
  "source": "Politica_Faturamento_2024.docx",
  "section": "Aprovação de Faturamento",
  "rule_id": "REGRA-FAT-001",
  "page": "12",
  "line_range": "89-90",
  "tipo_regra": "faturamento",
  "updated_at": "2024-01-15T10:00:00Z",
  "valid_from": "2024-01-01T00:00:00Z",
  "departamento": "Faturamento"
}
```

**Chunk 2:**
```
Texto: "Planos premium com procedimentos acima de R$ 1.000,00 devem passar por auditoria prévia. A auditoria deve ser concluída em até 48 horas."

Metadados:
{
  "source": "Politica_Faturamento_2024.docx",
  "section": "Aprovação de Faturamento",
  "rule_id": "REGRA-FAT-002",
  "page": "12",
  "line_range": "91-92",
  "tipo_regra": "auditoria",
  "updated_at": "2024-01-15T10:00:00Z",
  "valid_from": "2024-01-01T00:00:00Z",
  "departamento": "Faturamento"
}
```

#### Seção 2: Cobertura de Procedimentos

**Chunk 3:**
```
Texto: "Procedimento código 3344 (Consulta Cardiológica) é coberto para todos os planos. Procedimento código 5566 (Exame de Sangue Completo) requer autorização prévia para planos básicos."

Metadados:
{
  "source": "Politica_Faturamento_2024.docx",
  "section": "Cobertura de Procedimentos",
  "rule_id": "COBERTURA-PROC-3344",
  "page": "25",
  "line_range": "150-152",
  "tipo_regra": "cobertura",
  "updated_at": "2024-01-10T14:30:00Z",
  "valid_from": "2024-01-01T00:00:00Z",
  "departamento": "Cobertura"
}
```

## Exemplo de Uso na Ingestão

```python
from agent.rag.ingest import ingest_text

# Exemplo de ingestão com metadados completos
texto_regra = """
Procedimentos com valor acima de R$ 500,00 requerem aprovação humana 
antes do faturamento. Esta regra se aplica a todos os planos, 
exceto planos premium que possuem limite de R$ 1.000,00.
"""

metadata = {
    "source": "Politica_Faturamento_2024.docx",
    "section": "Aprovação de Faturamento",
    "rule_id": "REGRA-FAT-001",
    "page": "12",
    "line_range": "89-90",
    "tipo_regra": "faturamento",
    "updated_at": "2024-01-15T10:00:00Z",
    "valid_from": "2024-01-01T00:00:00Z",
    "departamento": "Faturamento"
}

# Ingestão (será implementada para aceitar metadados por chunk)
# ingest_text_with_metadata(texto_regra, metadata)
```

## Formato de Saída do RAG

Quando o nó `knowledge` busca regras, retorna uma lista estruturada:

```python
retrieved_rules = [
    {
        "text": "Procedimentos com valor acima de R$ 500,00 requerem aprovação...",
        "source": "Politica_Faturamento_2024.docx",
        "section": "Aprovação de Faturamento",
        "rule_id": "REGRA-FAT-001",
        "page": "12",
        "line_range": "89-90",
        "confidence": 0.92,  # Score de relevância da busca semântica
        "tipo_regra": "faturamento"
    }
]
```

## Boas Práticas

1. **Consistência nos IDs**: Use um padrão consistente para `rule_id` (ex: `REGRA-{TIPO}-{NUMERO}`)

2. **Seções Descritivas**: Use nomes de seção claros e específicos para facilitar navegação

3. **Versionamento**: Use `updated_at` e `valid_from` para rastrear mudanças nas regras

4. **Chunking Inteligente**: Mantenha regras completas em um único chunk quando possível, ou use `line_range` para rastrear chunks relacionados

5. **Metadados Enriquecidos**: Quanto mais metadados, melhor a rastreabilidade e filtragem

6. **Validação**: Valide metadados antes da ingestão para garantir consistência

## Próximos Passos

- Implementar função de ingestão que aceita metadados por chunk
- Criar validador de metadados
- Implementar filtros por `tipo_regra` e `valid_from` no RAG
- Adicionar endpoint de ingestão com validação de metadados
