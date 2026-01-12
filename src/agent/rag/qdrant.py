from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

# Configurações
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "empresa_m_regras"

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
        _vector_store = QdrantVectorStore(
            client=_get_client(),
            collection_name=COLLECTION_NAME,
            embedding=_get_embeddings()
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
    """
    results = _get_vector_store().similarity_search(query, k=k)

    return "\n\n".join([doc.page_content for doc in results])
