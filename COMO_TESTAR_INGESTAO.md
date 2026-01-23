# 🧪 Como Testar a Ingestão Manual

## 📄 Arquivo de Teste Criado

Foi criado o arquivo `docs_regras/Teste_Ingestao_Manual.txt` com 9 regras de teste para validar o sistema.

## 🚀 Testando o Endpoint de Ingestão por Arquivo

### 1. Verificar se o serviço está rodando

```bash
# Verificar se o container está rodando
docker ps | grep ingestion-service

# Verificar logs
docker-compose logs ingestion-service
```

### 2. Testar o endpoint de status

```bash
curl http://localhost:8001/ingestion/status
```

**Resposta esperada:**
```json
{
  "success": true,
  "message": "Status obtido com sucesso",
  "data": {
    "docs_path": "/app/docs_regras",
    "files_count": 3,
    "files": [
      "Contrato_Operadora_XYZ.txt",
      "Politica_Faturamento_2024.txt",
      "Teste_Ingestao_Manual.txt"
    ]
  }
}
```

### 3. Testar ingestão do arquivo específico

```bash
curl -X POST http://localhost:8001/ingestion/reindex/Teste_Ingestao_Manual.txt
```

**Resposta esperada:**
```json
{
  "success": true,
  "message": "Arquivo reindexado: 9 regras indexadas",
  "data": {
    "success": true,
    "rules_indexed": 9,
    "file": "Teste_Ingestao_Manual.txt",
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

### 4. Testar ingestão de todos os arquivos

```bash
curl -X POST http://localhost:8001/ingestion/reindex
```

**Resposta esperada:**
```json
{
  "success": true,
  "message": "Reindexação concluída: X regras indexadas",
  "data": {
    "success": true,
    "rules_indexed": X,
    "files_processed": 3,
    "files": [
      "Contrato_Operadora_XYZ.txt",
      "Politica_Faturamento_2024.txt",
      "Teste_Ingestao_Manual.txt"
    ],
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## 🔍 Verificar se as Regras Foram Indexadas

### Via API do Agente

```bash
# Testar busca que deve encontrar as regras de teste
curl -X POST http://localhost:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "procedimento código 9999 teste de sistema",
    "user_id": "test_user",
    "case_id": "TEST-001"
  }'
```

### Via Python

```python
from agent.rag.qdrant import search_docs_with_metadata

# Buscar regras de teste
results = search_docs_with_metadata("teste de sistema", k=5)

for doc in results:
    print(f"Rule ID: {doc.metadata.get('rule_id')}")
    print(f"Domain: {doc.metadata.get('domain')}")
    print(f"Text: {doc.page_content[:100]}...")
    print("---")
```

## 📊 Regras Esperadas no Arquivo de Teste

O arquivo `Teste_Ingestao_Manual.txt` contém:

1. **REGRA TEST-001** - Regra geral de teste
2. **REGRA TEST-002** - Regra sobre aprovação manual
3. **REGRA TEST-003** - Regra sobre validação
4. **REGRA VAL-001** - Validação de domínio
5. **REGRA VAL-002** - Validação de metadados
6. **REGRA VAL-003** - Validação de endpoint
7. **REGRA COB-TEST-001** - Cobertura de procedimento 9999
8. **REGRA COB-TEST-002** - Testes automatizados
9. **REGRA AUD-TEST-001** - Auditoria de testes
10. **REGRA AUD-TEST-002** - Validação manual

## ✅ Checklist de Validação

Após executar a ingestão, verifique:

- [ ] Status retorna o arquivo na lista
- [ ] Endpoint de reindexação retorna sucesso
- [ ] Número de regras indexadas está correto (9 regras)
- [ ] Busca no RAG encontra as regras de teste
- [ ] Metadados estão corretos (rule_id, domain, section)
- [ ] Logs mostram processamento correto

## 🐛 Troubleshooting

### Erro: "Arquivo não encontrado"
- Verifique se o arquivo está em `docs_regras/`
- Verifique se `INGESTION_DOCS_PATH` está configurado corretamente

### Erro: "Nenhuma regra encontrada"
- Verifique se o arquivo segue o formato correto (REGRA XXX-XXX: texto)
- Verifique os logs do parser

### Erro: "Erro ao conectar no Qdrant"
- Verifique se Qdrant está rodando: `docker ps | grep qdrant`
- Verifique variáveis `QDRANT_HOST` e `QDRANT_PORT`
