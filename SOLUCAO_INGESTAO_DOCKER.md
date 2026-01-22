# 🔧 Solução: Ingestão no Qdrant do Docker

## Problema Identificado

Você fez a ingestão usando `python scripts/ingest_regras_exemplo.py`, que conectou no Qdrant **local** (`localhost`), mas a API está rodando no **Docker** e busca no Qdrant do container (`qdrant`).

**Resultado:** Nenhuma regra encontrada porque são Qdrants diferentes!

## ✅ Solução: Fazer Ingestão no Qdrant do Docker

Você tem **2 opções**:

### Opção 1: Rodar Localmente Apontando para Docker (Recomendado)

O Qdrant do Docker está mapeado na porta `6333` do seu `localhost`, então você pode rodar localmente apontando para ele:

```powershell
# No PowerShell (Windows)
$env:QDRANT_HOST="localhost"
$env:QDRANT_PORT="6333"
python scripts/ingest_regras_docker.py
```

Ou em uma linha só:
```powershell
$env:QDRANT_HOST="localhost"; $env:QDRANT_PORT="6333"; python scripts/ingest_regras_docker.py
```

### Opção 2: Rodar Dentro do Container Docker

```powershell
docker-compose exec langgraph-api python scripts/ingest_regras_docker.py
```

## 📋 Passo a Passo Completo

1. **Verificar se o Qdrant está rodando:**
   ```powershell
   docker ps --filter "name=qdrant"
   ```
   Deve mostrar: `qdrant: Up X minutes`

2. **Executar a ingestão:**
   ```powershell
   $env:QDRANT_HOST="localhost"
   $env:QDRANT_PORT="6333"
   python scripts/ingest_regras_docker.py
   ```

3. **Verificar se funcionou:**
   Você deve ver mensagens como:
   ```
   Conectando no Qdrant: localhost:6333
   Indexando REGRA FAT-001...
   OK - REGRA FAT-001 indexada
   ...
   OK - Ingestao concluida! Total de 8 regras indexadas.
   ```

4. **Testar novamente:**
   ```powershell
   python test_api.py 1
   ```
   Agora deve encontrar regras! ✅

## 🔍 Verificação Adicional

Se ainda não funcionar, verifique:

1. **Qdrant está acessível:**
   ```powershell
   curl http://localhost:6333/collections
   ```
   Deve retornar JSON com as coleções.

2. **Verificar coleção criada:**
   ```powershell
   curl http://localhost:6333/collections/empresa_m_regras
   ```
   Deve mostrar informações da coleção.

3. **Verificar variáveis de ambiente da API:**
   Se a API está rodando no Docker, ela usa:
   - `QDRANT_HOST=qdrant` (nome do serviço Docker)
   - `QDRANT_PORT=6333`
   
   O script local deve usar:
   - `QDRANT_HOST=localhost` (mapeia para o container)
   - `QDRANT_PORT=6333`

## 📝 Nota Importante

O script `ingest_regras_docker.py` foi atualizado para incluir o campo `domain` em todos os metadados, necessário para o Domain Routing funcionar corretamente.

## ✅ Após a Ingestão Correta

Quando rodar os testes novamente, você deve ver:
- ✅ Regras encontradas: X (onde X > 0)
- ✅ Domínios nas regras: faturamento, planos_e_cobertura
- ✅ Filtro por domínio funcionando!
