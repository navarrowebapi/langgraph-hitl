# 📚 Serviço de Ingestão de Documentos - Guia Completo

## 🎯 Visão Geral

Este serviço fornece uma solução **reutilizável** para ingestão automatizada e manual de documentos em sistemas RAG. Ele pode ser facilmente adaptado para outros projetos apenas mudando a variável de ambiente `INGESTION_DOCS_PATH`.

## 🏗️ Arquitetura

```
services/ingestion/
├── __init__.py      # Módulo do serviço
├── parser.py        # Parser inteligente para arquivos de regras
├── service.py       # Lógica de ingestão reutilizável
├── api.py          # API REST para reindexação manual
└── scheduler.py    # Scheduler para execução automática às 6h
```

## 🚀 Funcionalidades

### 1. **Parser Inteligente** (`parser.py`)
- Extrai regras de arquivos `.txt` estruturados
- Identifica automaticamente:
  - Seções (SEÇÃO, CLÁUSULA)
  - IDs de regras (REGRA XXX-XXX, CLÁUSULA X.X)
  - Domínios (faturamento, juridico, planos_e_cobertura, etc.)
  - Tipos de regra (faturamento, auditoria, cobertura, etc.)
  - Departamentos

### 2. **Serviço de Ingestão** (`service.py`)
- Lógica central reutilizável
- Configuração via variáveis de ambiente
- Suporta ingestão de pasta completa ou arquivo específico

### 3. **API REST** (`api.py`)
- `POST /ingestion/reindex` - Reindexa todos os documentos
- `POST /ingestion/reindex/{filename}` - Reindexa um arquivo específico
- `GET /ingestion/status` - Status do serviço

### 4. **Scheduler Automático** (`scheduler.py`)
- Execução diária às 6:00 (configurável)
- Usa APScheduler para agendamento

### 5. **Busca Híbrida no RAG**
- Combina busca semântica (embeddings) + keywords/metadados
- Melhora precisão e recall
- Configurável via `semantic_weight`

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# Caminho para pasta com documentos (padrão: docs_regras/)
INGESTION_DOCS_PATH=./docs_regras

# Horário para execução automática (padrão: 06:00)
INGESTION_SCHEDULE_TIME=06:00

# Porta da API de ingestão (padrão: 8001)
INGESTION_API_PORT=8001

# Configurações do Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=empresa_m_regras

# OpenAI API Key (para embeddings)
OPENAI_API_KEY=sk-...
```

## 📖 Como Usar

### 1. **Reindexação Manual via API**

```bash
# Reindexar todos os documentos
curl -X POST http://localhost:8001/ingestion/reindex

# Reindexar um arquivo específico
curl -X POST http://localhost:8001/ingestion/reindex/Politica_Faturamento_2024.txt

# Verificar status
curl http://localhost:8001/ingestion/status
```

### 2. **Reindexação Manual via Python**

```python
from services.ingestion.service import IngestionService

# Inicializar serviço
service = IngestionService(docs_path="./docs_regras")

# Reindexar tudo
result = service.ingest_all()
print(f"Indexadas {result['rules_indexed']} regras")

# Reindexar arquivo específico
result = service.ingest_file("Politica_Faturamento_2024.txt")
```

### 3. **Execução Automática**

O scheduler roda automaticamente todos os dias às 6:00 (configurável via `INGESTION_SCHEDULE_TIME`).

## 🔄 Reutilização em Outros Projetos

Para usar este serviço em outro projeto:

1. **Copiar a pasta `services/ingestion/`** para o novo projeto
2. **Configurar variável de ambiente:**
   ```bash
   INGESTION_DOCS_PATH=/caminho/para/seu/projeto/docs
   ```
3. **Ajustar imports** se necessário (o serviço tenta importar de `agent.rag.ingest`)
4. **Rodar o serviço:**
   ```bash
   docker-compose up ingestion-service ingestion-scheduler
   ```

## 🔍 Busca Híbrida no RAG

A busca híbrida combina:

1. **Busca Semântica** (70% do peso padrão)
   - Usa embeddings para encontrar documentos semanticamente similares
   - Melhor para queries em linguagem natural

2. **Busca por Keywords** (30% do peso padrão)
   - Busca por palavras-chave específicas no texto
   - Melhor para termos técnicos, códigos, IDs

3. **Busca por Metadados** (boost adicional)
   - Filtro por `rule_id` específico
   - Filtro por `domain`
   - Boost para matches exatos

### Exemplo de Uso da Busca Híbrida

```python
from agent.rag.qdrant import search_docs_hybrid

# Busca híbrida com keywords
results = search_docs_hybrid(
    query="procedimento código 3344",
    k=5,
    keywords=["3344", "cardiológica"],
    domain="planos_e_cobertura",
    semantic_weight=0.7  # 70% semântica, 30% keywords
)
```

## 📊 Estrutura de Metadados

Cada regra indexada contém:

```python
{
    "source": "Politica_Faturamento_2024.txt",
    "section": "Aprovação de Faturamento",
    "rule_id": "REGRA-FAT-001",
    "page": "1",
    "line_range": "8-8",
    "tipo_regra": "faturamento",
    "domain": "faturamento",  # Para Domain Routing
    "updated_at": "2024-01-15T10:00:00Z",
    "valid_from": "2024-01-15T10:00:00Z",
    "departamento": "Faturamento"
}
```

## 🐳 Docker Compose

O serviço está configurado no `docker-compose.yml` com dois containers:

1. **ingestion-service**: API REST para reindexação manual
2. **ingestion-scheduler**: Scheduler para execução automática

### Comandos Úteis

```bash
# Subir todos os serviços
docker-compose up -d

# Ver logs do serviço de ingestão
docker-compose logs -f ingestion-service

# Ver logs do scheduler
docker-compose logs -f ingestion-scheduler

# Executar reindexação manual
docker-compose exec ingestion-service python -c "from services.ingestion.service import IngestionService; IngestionService().ingest_all()"
```

## 🔧 Troubleshooting

### Erro: "Pasta de documentos não encontrada"
- Verifique se `INGESTION_DOCS_PATH` está configurado corretamente
- Verifique se a pasta existe e tem permissões de leitura

### Erro: "Erro ao conectar no Qdrant"
- Verifique se o Qdrant está rodando: `docker ps | grep qdrant`
- Verifique as variáveis `QDRANT_HOST` e `QDRANT_PORT`

### Scheduler não executa
- Verifique os logs: `docker-compose logs ingestion-scheduler`
- Verifique o formato de `INGESTION_SCHEDULE_TIME` (deve ser HH:MM)

## 📝 Próximos Passos

- [ ] Suporte para outros formatos (PDF, DOCX)
- [ ] Webhook para notificar quando documentos são atualizados
- [ ] Interface web para gerenciar ingestão
- [ ] Suporte para múltiplas coleções
- [ ] Métricas e monitoramento
