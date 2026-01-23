# 📖 Explicação da Solução - Parte por Parte

## 🎯 Objetivo

Criar um serviço de ingestão **separado e reutilizável** que:
1. Execute automaticamente todos os dias às 6:00
2. Permita reindexação manual quando documentos são atualizados
3. Seja fácil de reutilizar em outros projetos (apenas mudar a pasta)

## 📁 Estrutura Criada

### 1. `services/ingestion/parser.py` - Parser Inteligente

**O que faz:**
- Lê arquivos `.txt` estruturados
- Extrai regras automaticamente usando regex
- Infere metadados automaticamente:
  - **Domain**: Analisa palavras-chave para determinar domínio (faturamento, juridico, etc.)
  - **Tipo de regra**: Identifica se é faturamento, auditoria, cobertura, etc.
  - **Departamento**: Infere baseado no domínio e seção

**Como funciona:**
```python
# Detecta padrões como:
# REGRA FAT-001: texto da regra...
# CLÁUSULA 1.1: texto da cláusula...

# E cria metadados automaticamente:
{
    "rule_id": "REGRA-FAT-001",
    "domain": "faturamento",  # Inferido do texto
    "tipo_regra": "faturamento",  # Inferido do texto
    "departamento": "Faturamento"  # Inferido do domain
}
```

**Por que é útil:**
- Não precisa configurar metadados manualmente
- Funciona com qualquer arquivo que siga o padrão
- Fácil de adaptar para outros formatos

---

### 2. `services/ingestion/service.py` - Lógica de Ingestão

**O que faz:**
- Lógica central reutilizável
- Configuração via variáveis de ambiente
- Suporta ingestão de pasta completa ou arquivo específico

**Como funciona:**
```python
# Inicializa com pasta configurável
service = IngestionService(docs_path="./docs_regras")

# Reindexa tudo
result = service.ingest_all()

# Ou reindexa arquivo específico
result = service.ingest_file("arquivo.txt")
```

**Por que é útil:**
- **Reutilizável**: Basta mudar `INGESTION_DOCS_PATH` para outro projeto
- **Desacoplado**: Não depende de código específico do projeto
- **Flexível**: Pode usar programaticamente ou via API

---

### 3. `services/ingestion/api.py` - API REST

**O que faz:**
- Expõe endpoints HTTP para reindexação manual
- Permite reindexar tudo ou arquivo específico
- Retorna estatísticas da ingestão

**Endpoints:**
- `POST /ingestion/reindex` - Reindexa todos os documentos
- `POST /ingestion/reindex/{filename}` - Reindexa arquivo específico
- `GET /ingestion/status` - Status do serviço

**Por que é útil:**
- **Manual**: Usuário pode reindexar quando atualizar documento
- **Integração**: Pode ser chamado por outros sistemas
- **Monitoramento**: Retorna estatísticas úteis

---

### 4. `services/ingestion/scheduler.py` - Scheduler Automático

**O que faz:**
- Executa ingestão automaticamente todos os dias às 6:00
- Usa APScheduler para agendamento
- Configurável via `INGESTION_SCHEDULE_TIME`

**Como funciona:**
```python
# Agenda execução diária
scheduler.add_job(
    run_ingestion,
    trigger=CronTrigger(hour=6, minute=0),
    id='daily_ingestion'
)
```

**Por que é útil:**
- **Automático**: Não precisa lembrar de rodar manualmente
- **Configurável**: Pode mudar horário via env var
- **Confiável**: Roda mesmo se o sistema reiniciar

---

### 5. `src/agent/rag/qdrant.py` - Busca Híbrida

**O que faz:**
- Adiciona função `search_docs_hybrid()` que combina:
  - **Busca semântica** (70%): Usa embeddings para entender contexto
  - **Busca por keywords** (30%): Busca por termos específicos no texto
  - **Busca por metadados**: Filtra por rule_id, domain, etc.

**Como funciona:**
```python
# Busca híbrida
results = search_docs_hybrid(
    query="procedimento código 3344",
    keywords=["3344", "cardiológica"],
    domain="planos_e_cobertura",
    semantic_weight=0.7  # 70% semântica, 30% keywords
)
```

**Por que é útil:**
- **Maior precisão**: Keywords garantem matches exatos
- **Maior recall**: Semântica encontra documentos relacionados
- **Flexível**: Pode ajustar pesos conforme necessidade

---

### 6. `src/agent/graph/nodes/knowledge.py` - Integração

**O que faz:**
- Atualizado para usar busca híbrida automaticamente
- Extrai keywords das entidades (procedimentos, medicamentos, etc.)
- Usa busca híbrida quando detecta keywords

**Como funciona:**
```python
# Se detecta procedimentos nas entidades
if entities.get("procedimentos"):
    keywords = [str(p) for p in entities["procedimentos"]]
    
    # Usa busca híbrida
    results = search_docs_hybrid(
        query=query,
        keywords=keywords,
        domain=domain_filter
    )
```

**Por que é útil:**
- **Automático**: Não precisa mudar código do agente
- **Inteligente**: Usa busca híbrida quando faz sentido
- **Fallback**: Usa busca semântica simples se não houver keywords

---

### 7. `docker-compose.yml` - Serviços Docker

**O que faz:**
- Adiciona dois novos serviços:
  - `ingestion-service`: API REST (porta 8001)
  - `ingestion-scheduler`: Scheduler automático

**Configuração:**
```yaml
ingestion-service:
  ports:
    - "8001:8001"
  environment:
    - INGESTION_DOCS_PATH=/app/docs_regras
    - INGESTION_SCHEDULE_TIME=06:00
  volumes:
    - ./docs_regras:/app/docs_regras
```

**Por que é útil:**
- **Isolado**: Serviço separado não afeta a API principal
- **Escalável**: Pode rodar em containers diferentes
- **Configurável**: Tudo via variáveis de ambiente

---

### 8. `pyproject.toml` - Dependências

**O que faz:**
- Adiciona `apscheduler>=3.10.4` para o scheduler

**Por que é útil:**
- **Leve**: APScheduler é uma biblioteca simples e confiável
- **Padrão**: Usado amplamente na comunidade Python

---

## 🔄 Fluxo Completo

### Execução Automática (6:00 diariamente)

```
1. Scheduler acorda às 6:00
   ↓
2. Chama IngestionService.ingest_all()
   ↓
3. Parser lê todos os arquivos de docs_regras/
   ↓
4. Extrai regras com metadados automáticos
   ↓
5. Indexa no Qdrant via agent.rag.ingest
   ↓
6. Logs mostram quantas regras foram indexadas
```

### Reindexação Manual (via API)

```
1. Usuário atualiza arquivo em docs_regras/
   ↓
2. Chama POST /ingestion/reindex/{filename}
   ↓
3. Parser lê apenas o arquivo atualizado
   ↓
4. Extrai regras com metadados
   ↓
5. Indexa no Qdrant
   ↓
6. Retorna estatísticas
```

### Busca Híbrida (quando RAG busca)

```
1. Agente recebe query com entidades
   ↓
2. Knowledge node extrai keywords das entidades
   ↓
3. Chama search_docs_hybrid() com:
   - Query semântica
   - Keywords extraídas
   - Domain filtrado
   ↓
4. Combina resultados:
   - 70% score semântico
   - 30% score de keywords
   - Boost para matches exatos
   ↓
5. Retorna regras ordenadas por relevância
```

---

## 🎨 Vantagens da Arquitetura

### 1. **Reutilizável**
- Basta copiar `services/ingestion/` para outro projeto
- Configurar `INGESTION_DOCS_PATH`
- Pronto!

### 2. **Desacoplado**
- Serviço separado não afeta API principal
- Pode rodar em containers diferentes
- Fácil de escalar

### 3. **Configurável**
- Tudo via variáveis de ambiente
- Não precisa mudar código
- Fácil de adaptar

### 4. **Inteligente**
- Parser infere metadados automaticamente
- Busca híbrida melhora resultados
- Scheduler automático

---

## 📊 Comparação: Antes vs Depois

### Antes:
- ❌ Script manual hardcoded
- ❌ Precisava rodar manualmente
- ❌ Metadados hardcoded no código
- ❌ Busca apenas semântica
- ❌ Difícil de reutilizar

### Depois:
- ✅ Serviço separado e reutilizável
- ✅ Execução automática + manual
- ✅ Metadados inferidos automaticamente
- ✅ Busca híbrida (semântica + keywords)
- ✅ Fácil de reutilizar (só mudar pasta)

---

## 🚀 Próximos Passos Sugeridos

1. **Testar ingestão manual:**
   ```bash
   curl -X POST http://localhost:8001/ingestion/reindex
   ```

2. **Verificar scheduler:**
   ```bash
   docker-compose logs ingestion-scheduler
   ```

3. **Testar busca híbrida:**
   - Fazer query com procedimentos específicos
   - Verificar se encontra regras corretas

4. **Adaptar para outros projetos:**
   - Copiar `services/ingestion/`
   - Configurar `INGESTION_DOCS_PATH`
   - Pronto!

---

## 💡 Dicas

- **Para mudar horário**: Ajuste `INGESTION_SCHEDULE_TIME` no `.env`
- **Para mudar pasta**: Ajuste `INGESTION_DOCS_PATH` no `.env`
- **Para ajustar busca híbrida**: Mude `semantic_weight` em `knowledge.py`
- **Para debug**: Veja logs com `docker-compose logs -f`
