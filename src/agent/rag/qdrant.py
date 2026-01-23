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


def search_docs_hybrid(
    query: str,
    k: int = 5,
    domain: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    rule_ids: Optional[list[str]] = None,
    semantic_weight: float = 0.7
) -> list[Document]:
    """
    Busca híbrida: combina busca semântica com filtros por keywords/metadados
    
    Args:
        query: Texto de busca semântica
        k: Número de resultados a retornar
        domain: Domínio para filtrar (opcional)
        keywords: Lista de palavras-chave para buscar no texto (opcional)
        rule_ids: Lista de IDs de regras específicas para buscar (opcional)
        semantic_weight: Peso da busca semântica (0.0 a 1.0). Resto é peso de keywords.
                         Padrão: 0.7 (70% semântica, 30% keywords)
        
    Returns:
        Lista de Document com metadados completos, ordenados por relevância combinada
    """
    try:
        vector_store = _get_vector_store()
        client = _get_client()
        
        # 1. BUSCA SEMÂNTICA (embeddings)
        semantic_results = vector_store.similarity_search_with_score(
            query, 
            k=k*5 if (keywords or rule_ids) else k*2  # Buscar mais para combinar depois
        )
        
        # Normalizar scores semânticos (0 a 1)
        if semantic_results:
            max_score = max(score for _, score in semantic_results)
            min_score = min(score for _, score in semantic_results)
            score_range = max_score - min_score if max_score != min_score else 1.0
        else:
            score_range = 1.0
        
        # 2. BUSCA POR KEYWORDS (se fornecido)
        keyword_results = []
        if keywords:
            # Buscar por palavras-chave no texto usando Qdrant filter
            # Nota: Qdrant não tem busca full-text nativa, então fazemos busca semântica
            # e depois filtramos por keywords no texto
            keyword_query = " ".join(keywords)
            keyword_semantic = vector_store.similarity_search_with_score(keyword_query, k=k*3)
            keyword_results = keyword_semantic
        
        # 3. BUSCA POR RULE_IDS (se fornecido)
        rule_id_results = []
        if rule_ids:
            # Buscar documentos com rule_ids específicos usando filtro do Qdrant
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchAny
                
                # Criar filtro para rule_ids
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="rule_id",
                            match=MatchAny(any=rule_ids)
                        )
                    ]
                )
                
                # Buscar com filtro (requer usar cliente Qdrant diretamente)
                # Como QdrantVectorStore não suporta filtros facilmente,
                # vamos buscar todos e filtrar depois
                all_docs = vector_store.similarity_search_with_score(query, k=k*10)
                rule_id_results = [
                    (doc, score) for doc, score in all_docs
                    if doc.metadata.get("rule_id") in rule_ids
                ]
            except Exception as e:
                print(f"[WARNING Qdrant] Erro ao buscar por rule_ids: {e}")
        
        # 4. COMBINAR RESULTADOS
        combined_scores = {}
        
        # Adicionar resultados semânticos
        for doc, score in semantic_results:
            doc_id = doc.metadata.get("rule_id", id(doc))
            # Normalizar score semântico
            normalized_score = (score - min_score) / score_range if score_range > 0 else 0.5
            combined_scores[doc_id] = {
                "doc": doc,
                "semantic_score": normalized_score * semantic_weight,
                "keyword_score": 0.0,
                "rule_id_match": False
            }
        
        # Adicionar boost de keywords
        if keywords:
            for doc, score in keyword_results:
                doc_id = doc.metadata.get("rule_id", id(doc))
                text_lower = doc.page_content.lower()
                keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
                keyword_score = (keyword_matches / len(keywords)) * (1 - semantic_weight)
                
                if doc_id in combined_scores:
                    combined_scores[doc_id]["keyword_score"] = keyword_score
                else:
                    combined_scores[doc_id] = {
                        "doc": doc,
                        "semantic_score": 0.0,
                        "keyword_score": keyword_score,
                        "rule_id_match": False
                    }
        
        # Boost para rule_ids específicos
        if rule_ids:
            for doc, score in rule_id_results:
                doc_id = doc.metadata.get("rule_id", id(doc))
                if doc_id in rule_ids:
                    if doc_id in combined_scores:
                        combined_scores[doc_id]["rule_id_match"] = True
                        # Boost de 20% para match exato de rule_id
                        combined_scores[doc_id]["semantic_score"] *= 1.2
                    else:
                        combined_scores[doc_id] = {
                            "doc": doc,
                            "semantic_score": 0.8,  # Score alto para match exato
                            "keyword_score": 0.0,
                            "rule_id_match": True
                        }
        
        # 5. CALCULAR SCORE FINAL E ORDENAR
        final_results = []
        for doc_id, scores in combined_scores.items():
            final_score = (
                scores["semantic_score"] + 
                scores["keyword_score"] +
                (0.1 if scores["rule_id_match"] else 0.0)  # Bonus para match exato
            )
            final_results.append((scores["doc"], final_score))
        
        # Ordenar por score final (maior primeiro)
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        # 6. FILTRAR POR DOMAIN (se fornecido)
        if domain:
            filtered_results = [
                (doc, score) for doc, score in final_results
                if doc.metadata.get("domain") == domain
            ]
            results = filtered_results[:k]
        else:
            results = final_results[:k]
        
        # 7. PREPARAR RESULTADO FINAL
        docs_with_metadata = []
        for doc, score in results:
            doc.metadata["score"] = float(score)
            doc.metadata["hybrid_score"] = float(score)  # Score combinado
            docs_with_metadata.append(doc)
        
        print(f"[DEBUG Qdrant Hybrid] Busca híbrida: {len(docs_with_metadata)} resultados")
        if keywords:
            print(f"   Keywords: {keywords}")
        if rule_ids:
            print(f"   Rule IDs: {rule_ids}")
        
        return docs_with_metadata
        
    except Exception as e:
        print(f"[WARNING Qdrant] Erro na busca híbrida: {e}. Fallback para busca semântica...")
        # Fallback para busca semântica simples
        return search_docs_with_metadata(query, k=k, domain=domain)
