# 🚀 Serviço de Ingestão de Documentos - Guia Rápido

## 📋 Resumo

Solução completa para ingestão **automatizada** e **manual** de documentos no sistema RAG, com:
- ✅ **Serviço separado e reutilizável** (basta mudar a pasta via env var)
- ✅ **Busca híbrida** (semântica + keywords/metadados)
- ✅ **Execução automática** diária às 6:00
- ✅ **API REST** para reindexação manual
- ✅ **Parser inteligente** que extrai metadados automaticamente

## 🏗️ Estrutura Criada

```
langgraph-hitl/
├── services/
│   └── ingestion/          # 🆕 Serviço reutilizável
│       ├── parser.py       # Parser inteligente
│       ├── service.py      # Lógica de ingestão
│       ├── api.py         # API REST
│       └── scheduler.py   # Scheduler automático
├── src/
│   └── agent/
│       └── rag/
│           └── qdrant.py   # ✨ Adicionada busca híbrida
└── docker-compose.yml      # ✨ Adicionados serviços de ingestão
```

## 🚀 Como Usar

### 1. Configurar Variáveis de Ambiente

Adicione ao seu `.env`:

```bash
# Pasta com documentos (padrão: docs_regras/)
INGESTION_DOCS_PATH=./docs_regras

# Horário para execução automática (padrão: 06:00)
INGESTION_SCHEDULE_TIME=06:00

# Porta da API de ingestão (padrão: 8001)
INGESTION_API_PORT=8001
```

### 2. Subir os Serviços

```bash
docker-compose up -d
```

Isso sobe:
- `langgraph-api` (porta 8000) - API principal
- `ingestion-service` (porta 8001) - API de ingestão
- `ingestion-scheduler` - Scheduler automático

### 3. Reindexação Manual

#### Via API REST:
```bash
# Reindexar todos os documentos
curl -X POST http://localhost:8001/ingestion/reindex

# Reindexar arquivo específico
curl -X POST http://localhost:8001/ingestion/reindex/Politica_Faturamento_2024.txt

# Verificar status
curl http://localhost:8001/ingestion/status
```

#### Via Python:
```python
from services.ingestion.service import IngestionService

service = IngestionService()
result = service.ingest_all()
print(f"Indexadas {result['rules_indexed']} regras")
```

### 4. Execução Automática

O scheduler executa automaticamente todos os dias às 6:00 (configurável via `INGESTION_SCHEDULE_TIME`).

Para ver logs:
```bash
docker-compose logs -f ingestion-scheduler
```

## 🔍 Busca Híbrida

O sistema agora usa **busca híbrida** automaticamente quando detecta keywords nas entidades:

- **70% busca semântica** (embeddings) - entende contexto
- **30% busca por keywords** - matches exatos de termos técnicos
- **Boost adicional** para rule_ids específicos

### Exemplo:

Quando o sistema detecta `procedimentos: ["3344"]` nas entidades, ele:
1. Busca semanticamente por "procedimento código 3344"
2. Dá boost para documentos que contêm "3344" no texto
3. Prioriza regras com `rule_id` relacionado

## 🔄 Reutilização em Outros Projetos

Para usar em outro projeto:

1. **Copie a pasta `services/ingestion/`** para o novo projeto
2. **Configure a variável de ambiente:**
   ```bash
   INGESTION_DOCS_PATH=/caminho/para/seu/projeto/docs
   ```
3. **Ajuste os imports** se necessário (o serviço importa de `agent.rag.ingest`)
4. **Pronto!** O serviço funciona da mesma forma

## 📚 Documentação Completa

- [Guia do Serviço de Ingestão](docs/SERVICO_INGESTAO.md) - Documentação completa
- [Busca Híbrida](docs/BUSCA_HIBRIDA.md) - Detalhes técnicos da busca híbrida

## 🐛 Troubleshooting

### Erro: "Pasta de documentos não encontrada"
- Verifique `INGESTION_DOCS_PATH` no `.env`
- Verifique se a pasta existe e tem permissões

### Erro: "Erro ao conectar no Qdrant"
- Verifique se Qdrant está rodando: `docker ps | grep qdrant`
- Verifique `QDRANT_HOST` e `QDRANT_PORT`

### Scheduler não executa
- Verifique logs: `docker-compose logs ingestion-scheduler`
- Verifique formato de `INGESTION_SCHEDULE_TIME` (deve ser HH:MM)

## ✨ Próximos Passos

1. Testar a ingestão manual via API
2. Verificar se o scheduler está agendado corretamente
3. Testar a busca híbrida com queries que contenham keywords
4. Ajustar `semantic_weight` conforme necessário
