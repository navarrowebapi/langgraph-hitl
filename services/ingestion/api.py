"""
API REST para Serviço de Ingestão

Endpoints:
- POST /ingestion/reindex - Reindexa todos os documentos
- POST /ingestion/reindex/{filename} - Reindexa um arquivo específico
- GET /ingestion/status - Status do serviço
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys
from pathlib import Path

# Adicionar src ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from services.ingestion.service import IngestionService

app = FastAPI(
    title="Serviço de Ingestão de Documentos",
    description="API para ingestão e reindexação de documentos no RAG",
    version="1.0.0"
)


class IngestionResponse(BaseModel):
    """Resposta padrão da API de ingestão"""
    success: bool
    message: str
    data: Optional[dict] = None


# Inicializar serviço
ingestion_service = IngestionService()


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "service": "Ingestion Service",
        "version": "1.0.0",
        "docs_path": ingestion_service.docs_path
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}


@app.get("/ingestion/status", response_model=IngestionResponse)
async def get_status():
    """
    Retorna status do serviço de ingestão
    
    Returns:
        Status com informações sobre arquivos disponíveis
    """
    try:
        status = ingestion_service.get_status()
        return IngestionResponse(
            success=True,
            message="Status obtido com sucesso",
            data=status
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter status: {str(e)}"
        )


@app.post("/ingestion/reindex", response_model=IngestionResponse)
async def reindex_all():
    """
    Reindexa todos os documentos da pasta configurada
    
    Returns:
        Estatísticas da ingestão
    """
    try:
        result = ingestion_service.ingest_all()
        
        if result["success"]:
            return IngestionResponse(
                success=True,
                message=f"Reindexação concluída: {result['rules_indexed']} regras indexadas",
                data=result
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Erro desconhecido na ingestão")
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reindexar: {str(e)}"
        )


@app.post("/ingestion/reindex/{filename}", response_model=IngestionResponse)
async def reindex_file(filename: str):
    """
    Reindexa um arquivo específico
    
    Args:
        filename: Nome do arquivo (deve estar na pasta configurada)
        
    Returns:
        Estatísticas da ingestão do arquivo
    """
    try:
        result = ingestion_service.ingest_file(filename)
        
        if result["success"]:
            return IngestionResponse(
                success=True,
                message=f"Arquivo reindexado: {result['rules_indexed']} regras indexadas",
                data=result
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Arquivo não encontrado")
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reindexar arquivo: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("INGESTION_API_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
