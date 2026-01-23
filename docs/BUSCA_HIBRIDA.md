# 🔍 Busca Híbrida no RAG - Documentação Técnica

## 📋 Visão Geral

A busca híbrida combina **busca semântica** (embeddings) com **busca por keywords/metadados** para melhorar tanto a precisão quanto o recall do sistema RAG.

## 🎯 Por que Busca Híbrida?

### Limitações da Busca Semântica Pura
- Pode perder documentos com termos técnicos específicos
- Dificuldade em encontrar IDs de regras específicas
- Pode retornar resultados semanticamente similares mas não relevantes

### Limitações da Busca por Keywords Pura
- Não entende sinônimos ou variações linguísticas
- Dificuldade com queries em linguagem natural
- Pode perder documentos relevantes com palavras diferentes

### Solução: Combinação Inteligente
A busca híbrida combina o melhor dos dois mundos:
- **Semântica** para entender contexto e significado
- **Keywords** para matches exatos de termos técnicos
- **Metadados** para filtros precisos

## 🔧 Implementação

### Função Principal

```python
def search_docs_hybrid(
    query: str,
    k: int = 5,
    domain: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    rule_ids: Optional[list[str]] = None,
    semantic_weight: float = 0.7
) -> list[Document]:
```

### Parâmetros

- `query`: Texto de busca semântica
- `k`: Número de resultados a retornar
- `domain`: Filtrar por domínio (faturamento, juridico, etc.)
- `keywords`: Lista de palavras-chave para buscar no texto
- `rule_ids`: Lista de IDs de regras específicas
- `semantic_weight`: Peso da busca semântica (0.0 a 1.0)
  - `0.7` = 70% semântica, 30% keywords (padrão)
  - `1.0` = 100% semântica (busca pura)
  - `0.0` = 100% keywords (busca por termos)

## 📊 Algoritmo de Combinação

### 1. Busca Semântica
```python
semantic_results = vector_store.similarity_search_with_score(query, k=k*5)
# Normaliza scores para 0-1
normalized_score = (score - min_score) / score_range
final_score = normalized_score * semantic_weight
```

### 2. Busca por Keywords
```python
# Conta matches de keywords no texto
keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
keyword_score = (keyword_matches / len(keywords)) * (1 - semantic_weight)
```

### 3. Boost por Rule IDs
```python
# Se rule_id está na lista, boost de 20%
if rule_id in rule_ids:
    semantic_score *= 1.2
```

### 4. Score Final
```python
final_score = (
    semantic_score +      # 70% (padrão)
    keyword_score +       # 30% (padrão)
    rule_id_bonus         # +10% se match exato
)
```

## 💡 Exemplos de Uso

### Exemplo 1: Busca com Keywords

```python
from agent.rag.qdrant import search_docs_hybrid

# Buscar regras sobre procedimento específico
results = search_docs_hybrid(
    query="consulta cardiológica",
    keywords=["3344", "cardiológica"],
    k=5
)
```

**Resultado**: Encontra regras que mencionam "consulta cardiológica" semanticamente E que contêm o código "3344" ou a palavra "cardiológica".

### Exemplo 2: Busca por Rule ID Específico

```python
# Buscar regra específica por ID
results = search_docs_hybrid(
    query="aprovação de faturamento",
    rule_ids=["REGRA-FAT-001"],
    k=5
)
```

**Resultado**: Prioriza a regra FAT-001 mesmo que outras sejam semanticamente mais similares.

### Exemplo 3: Busca com Filtro de Domínio

```python
# Buscar apenas regras de faturamento
results = search_docs_hybrid(
    query="valor acima de 500",
    domain="faturamento",
    keywords=["500", "aprovação"],
    k=5
)
```

**Resultado**: Retorna apenas regras do domínio "faturamento" que mencionam valores acima de 500.

## 🔄 Integração no Knowledge Node

O nó `knowledge.py` usa busca híbrida automaticamente quando detecta keywords nas entidades:

```python
# Extrair keywords das entidades
keywords = []
if entities.get("procedimentos"):
    keywords.extend([str(p) for p in entities["procedimentos"]])

# Usar busca híbrida se houver keywords
if keywords:
    results = search_docs_hybrid(
        query=query,
        k=5,
        domain=domain_filter,
        keywords=keywords,
        semantic_weight=0.7
    )
else:
    # Fallback para busca semântica simples
    results = search_docs_with_metadata(query, k=5, domain=domain_filter)
```

## 📈 Benefícios

1. **Maior Precisão**: Keywords garantem matches exatos de termos técnicos
2. **Maior Recall**: Semântica encontra documentos relacionados mesmo com palavras diferentes
3. **Flexibilidade**: Pode ajustar pesos conforme necessidade
4. **Rastreabilidade**: Rule IDs permitem referenciar regras específicas

## ⚙️ Configuração Avançada

### Ajustar Pesos

Para queries mais técnicas (mais keywords):
```python
results = search_docs_hybrid(
    query=query,
    keywords=keywords,
    semantic_weight=0.5  # 50% semântica, 50% keywords
)
```

Para queries mais naturais (mais semântica):
```python
results = search_docs_hybrid(
    query=query,
    keywords=keywords,
    semantic_weight=0.9  # 90% semântica, 10% keywords
)
```

## 🐛 Debug

Para ver detalhes da busca híbrida, verifique os logs:

```
[DEBUG Qdrant Hybrid] Busca híbrida: 5 resultados
   Keywords: ['3344', 'cardiológica']
   Rule IDs: None
```

## 📚 Referências

- [Qdrant Hybrid Search](https://qdrant.tech/documentation/concepts/search/#hybrid-search)
- [LangChain Qdrant Integration](https://python.langchain.com/docs/integrations/vectorstores/qdrant)
