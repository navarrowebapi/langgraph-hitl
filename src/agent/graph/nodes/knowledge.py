from agent.graph.state import WorkflowState
from agent.rag.qdrant import search_docs, search_docs_with_metadata


def retrieve_knowledge(state: WorkflowState) -> WorkflowState:
    """
    Busca regras relevantes no repositório de conhecimento usando RAG.
    Constrói query semântica a partir de intent e entities.
    Retorna regras estruturadas com metadados completos.
    """
    # Construir query contextualizada a partir de intent e entities
    intent = state.get("intent", "")
    entities = state.get("entities", {})
    
    # Construir query semântica
    query_parts = []
    if intent:
        query_parts.append(f"Intenção: {intent}")
    
    # Adicionar informações relevantes das entidades
    if entities:
        entity_info = []
        if "procedimentos" in entities:
            procs = entities["procedimentos"]
            if isinstance(procs, list):
                entity_info.append(f"Procedimentos: {', '.join(map(str, procs))}")
            else:
                entity_info.append(f"Procedimento: {procs}")
        
        if "valor_total" in entities or "valor" in entities:
            valor = entities.get("valor_total") or entities.get("valor", 0)
            entity_info.append(f"Valor: R$ {valor}")
        
        if "plano" in entities:
            entity_info.append(f"Plano: {entities['plano']}")
        
        if entity_info:
            query_parts.append("Contexto: " + ", ".join(entity_info))
    
    # Se não houver query construída, usar input_text como fallback
    query = "\n".join(query_parts) if query_parts else state.get("input_text", "")
    
    # Buscar regras com metadados completos
    try:
        # Debug: imprimir query (pode remover depois)
        print(f"[DEBUG Knowledge] Query construída: {query}")
        
        results = search_docs_with_metadata(query, k=5)
        
        print(f"[DEBUG Knowledge] Encontrados {len(results)} resultados")
        
        # Formatar regras estruturadas
        retrieved_rules = []
        for doc in results:
            rule = {
                "text": doc.page_content,
                "source": doc.metadata.get("source", "desconhecido"),
                "section": doc.metadata.get("section", ""),
                "rule_id": doc.metadata.get("rule_id", ""),
                "page": doc.metadata.get("page", ""),
                "line_range": doc.metadata.get("line_range", ""),
                "confidence": doc.metadata.get("score", 0.0),
                "tipo_regra": doc.metadata.get("tipo_regra", ""),
            }
            retrieved_rules.append(rule)
        
        # Manter retrieved_context para compatibilidade (texto concatenado)
        if retrieved_rules:
            retrieved_context = "\n\n".join([
                f"[{r['source']}] {r['text']}" 
                for r in retrieved_rules
            ])
        else:
            retrieved_context = "Nenhuma regra encontrada para esta consulta."
        
        print(f"[DEBUG Knowledge] Retornando {len(retrieved_rules)} regras")
        
        return {
            "retrieved_context": retrieved_context,
            "retrieved_rules": retrieved_rules
        }
    except Exception as e:
        # Em caso de erro, retornar valores padrão com informação do erro
        import traceback
        error_msg = f"Erro ao buscar regras: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR Knowledge] {error_msg}")
        return {
            "retrieved_context": error_msg,
            "retrieved_rules": []
        }
