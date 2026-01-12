# Docker Setup para Qdrant

Este projeto usa o Qdrant como banco de dados vetorial para funcionalidades de RAG (Retrieval-Augmented Generation).

## Pré-requisitos

- Docker instalado
- Docker Compose instalado

## Como usar

### Iniciar o Qdrant

```bash
docker-compose up -d
```

Isso irá:
- Baixar a imagem oficial do Qdrant (se ainda não tiver)
- Iniciar o container na porta 6333 (API REST) e 6334 (gRPC)
- Criar um volume persistente para os dados

### Verificar se está rodando

```bash
docker-compose ps
```

Ou acesse: http://localhost:6333/dashboard

### Parar o Qdrant

```bash
docker-compose down
```

### Parar e remover os dados

```bash
docker-compose down -v
```

⚠️ **Atenção**: O comando acima remove o volume com todos os dados armazenados!

### Ver logs

```bash
docker-compose logs -f qdrant
```

## Configuração

O Qdrant está configurado para:
- **Host**: localhost
- **Porta HTTP**: 6333
- **Porta gRPC**: 6334
- **Collection**: `empresa_m_regras` (definida no código)

Os dados são persistidos no volume Docker `qdrant_storage`, então mesmo após parar e iniciar novamente, os dados permanecem.

### Variáveis de Ambiente (Opcional)

Se você quiser personalizar a configuração do Qdrant, pode criar um arquivo `.env` na raiz do projeto com:

```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=empresa_m_regras
```

E então atualizar o arquivo `src/agent/rag/qdrant.py` para ler essas variáveis:

```python
import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "empresa_m_regras")
```

## Troubleshooting

### Porta já em uso

Se a porta 6333 já estiver em uso, você pode alterar no `docker-compose.yml`:

```yaml
ports:
  - "6335:6333"  # Mude 6335 para outra porta disponível
```

E atualize o `QDRANT_PORT` no arquivo `src/agent/rag/qdrant.py`.

### Verificar saúde do container

```bash
docker-compose ps
```

O status deve mostrar "healthy" após alguns segundos.
