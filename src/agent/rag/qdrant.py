import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from dotenv import load_dotenv
from typing import Optional

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações - usando variáveis de ambiente para produção
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "empresa_m_regras")

# Embeddings (lazy)
_embeddings = None
_client = None
_vector_store = None


def _get_embeddings():
    """Retorna embeddings (singleton)"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return _embeddings


def _reset_connections():
    """Reseta todas as conexões (útil para mudar de Qdrant)"""
    global _client, _vector_store, _embeddings
    _client = None
    _vector_store = None
    _embeddings = None


def _get_client():
    """Retorna cliente Qdrant (singleton)"""
    global _client, QDRANT_HOST, QDRANT_PORT
    # Re-ler variáveis de ambiente para garantir valores atualizados
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    
    if _client is None:
        _client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT
        )
    return _client


def _get_vector_store():
    """Retorna vector store (singleton, lazy initialization)"""
    global _vector_store, COLLECTION_NAME
    # Re-ler variáveis de ambiente para garantir valores atualizados
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "empresa_m_regras")
    
    if _vector_store is None:
        client = _get_client()
        embeddings = _get_embeddings()
        
        # Verificar se a coleção existe, se não existir criar
        try:
            client.get_collection(COLLECTION_NAME)
        except Exception:
            # Coleção não existe, criar automaticamente
            from qdrant_client.models import Distance, VectorParams
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small tem 1536 dimensões
                    distance=Distance.COSINE
                )
            )
        
        # QdrantVectorStore agora pode ser criado com a coleção existente
        _vector_store = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings
        )
    return _vector_store


def add_documents(texts: list[str], metadata: list[dict] | None = None):
    """
    Indexa textos no Qdrant
    """
    docs = []

    for i, text in enumerate(texts):
        docs.append(
            Document(
                page_content=text,
                metadata=metadata[i] if metadata else {}
            )
        )

    _get_vector_store().add_documents(docs)


def search_docs(query: str, k: int = 4) -> str:
    """
    Busca semântica no Qdrant
    Retorna texto concatenado (RAG-friendly)
    Mantido para compatibilidade com código existente
    """
    results = _get_vector_store().similarity_search(query, k=k)

    return "\n\n".join([doc.page_content for doc in results])


def search_docs_with_metadata(
    query: str, 
    k: int = 5, 
    domain: Optional[str] = None
) -> list[Document]:
    """
    Busca semântica no Qdrant com metadados completos e filtro opcional por domínio
    
    Args:
        query: Texto de busca semântica
        k: Número de resultados a retornar
        domain: Domínio para filtrar (opcional). Se fornecido, retorna apenas regras desse domínio.
                Valores válidos: faturamento, juridico, planos_e_cobertura, cadastro, atendimento, outros
        
    Returns:
        Lista de Document com metadados completos (source, section, rule_id, domain, etc)
    """
    try:
        vector_store = _get_vector_store()
        
        # Buscar resultados (sempre sem filtro no nível do Qdrant)
        # O LangChain QdrantVectorStore não suporta filtros nativos facilmente
        # Vamos fazer busca semântica e filtrar pelos metadados depois
        all_results = vector_store.similarity_search_with_score(query, k=k*3 if domain else k)
        
        # Filtrar por domain se fornecido
        if domain:
            print(f"[DEBUG Qdrant] Filtrando por domínio: {domain}")
            filtered_results = [
                (doc, score) for doc, score in all_results 
                if doc.metadata.get("domain") == domain
            ]
            results = filtered_results[:k]  # Limitar ao número solicitado
            print(f"[DEBUG Qdrant] Encontrados {len(filtered_results)} resultados após filtro (de {len(all_results)} total)")
        else:
            results = all_results[:k]
        
        docs_with_metadata = []
        for doc, score in results:
            # Adicionar score aos metadados
            doc.metadata["score"] = float(score)
            docs_with_metadata.append(doc)
        
        return docs_with_metadata
    except Exception as e:
        # Se houver erro com filtro, tentar busca sem filtro como fallback
        print(f"[WARNING Qdrant] Erro ao buscar com filtro: {e}. Tentando busca sem filtro...")
        try:
            results = _get_vector_store().similarity_search_with_score(query, k=k)
            docs_with_metadata = []
            for doc, score in results:
                doc.metadata["score"] = float(score)
                docs_with_metadata.append(doc)
            return docs_with_metadata
        except Exception as e2:
            # Se similarity_search_with_score não estiver disponível, usar fallback básico
            results = _get_vector_store().similarity_search(query, k=k)
            for doc in results:
                doc.metadata["score"] = 0.0  # Score padrão se não disponível
            return results
