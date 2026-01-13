FROM python:3.11-slim

# Metadados
LABEL maintainer="LangGraph Agent"
LABEL description="API FastAPI para LangGraph Agent"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de dependências primeiro (para cache do Docker)
COPY pyproject.toml ./

# Instalar dependências básicas incluindo debugpy para debug remoto
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir debugpy

# Copiar código fonte
COPY . .

# Instalar o projeto e suas dependências
RUN pip install --no-cache-dir -e .

# Expor porta da API e porta de debug remoto
EXPOSE 8000 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a API com debugpy
# --wait-for-client: aguarda conexão do debugger antes de iniciar
# Remova --wait-for-client se quiser que a API inicie normalmente e você conecte depois
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m", "uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
