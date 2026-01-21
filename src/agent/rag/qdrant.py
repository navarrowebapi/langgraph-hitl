import os
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from dotenv import load_dotenv

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


def _get_client():
    """Retorna cliente Qdrant (singleton)"""
    global _client
    if _client is None:
        _client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT
        )
    return _client


def _get_vector_store():
    """Retorna vector store (singleton, lazy initialization)"""
    global _vector_store
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


def search_docs_with_metadata(query: str, k: int = 5) -> list[Document]:
    """
    Busca semântica no Qdrant com metadados completos
    Retorna lista de Document com page_content e metadata incluindo score
    
    Args:
        query: Texto de busca semântica
        k: Número de resultados a retornar
        
    Returns:
        Lista de Document com metadados completos (source, section, rule_id, etc)
    """
    try:
        # Usar similarity_search_with_score para obter scores de relevância
        results = _get_vector_store().similarity_search_with_score(query, k=k)
        
        docs_with_metadata = []
        for doc, score in results:
            # Adicionar score aos metadados
            doc.metadata["score"] = float(score)
            docs_with_metadata.append(doc)
        
        return docs_with_metadata
    except Exception as e:
        # Se similarity_search_with_score não estiver disponível, usar fallback
        results = _get_vector_store().similarity_search(query, k=k)
        for doc in results:
            doc.metadata["score"] = 0.0  # Score padrão se não disponível
        return results
