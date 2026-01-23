from agent.graph.state import WorkflowState
from agent.rag.qdrant import search_docs, search_docs_with_metadata, search_docs_hybrid


def retrieve_knowledge(state: WorkflowState) -> WorkflowState:
    """
    Busca regras relevantes no repositório de conhecimento usando RAG.
    Constrói query semântica combinando input_text completo com intent e entities.
    Retorna regras estruturadas com metadados completos.
    """
    input_text = state.get("input_text", "")
    intent = state.get("intent", "")
    entities = state.get("entities", {})
    
    # Construir query semântica combinando texto completo + informações estruturadas
    # O texto completo fornece contexto semântico rico para embeddings
    # Intent e entities estruturados ajudam a focar a busca
    query_parts = []
    
    # 1. Texto completo como base (mais contexto semântico)
    if input_text:
        query_parts.append(input_text)
    
    # 2. Adicionar informações estruturadas para dar foco
    structured_info = []
    if intent:
        # Intent agora representa o domínio (faturamento, juridico, planos_e_cobertura, etc.)
        structured_info.append(f"Domínio identificado: {intent}")
    
    # Adicionar informações relevantes das entidades
    if entities:
        if "procedimentos" in entities:
            procs = entities["procedimentos"]
            if isinstance(procs, list):
                structured_info.append(f"Procedimentos mencionados: {', '.join(map(str, procs))}")
            else:
                structured_info.append(f"Procedimento mencionado: {procs}")
        
        if "valor_total" in entities or "valor" in entities:
            valor = entities.get("valor_total") or entities.get("valor", 0)
            structured_info.append(f"Valor total: R$ {valor}")
        
        if "plano" in entities:
            structured_info.append(f"Plano: {entities['plano']}")
        
        if "medicacoes" in entities:
            meds = entities["medicacoes"]
            if isinstance(meds, list):
                structured_info.append(f"Medicações: {', '.join(map(str, meds))}")
            else:
                structured_info.append(f"Medicação: {meds}")
        
        if "localidade" in entities:
            structured_info.append(f"Localidade: {entities['localidade']}")
    
    # Combinar tudo em uma query rica
    if structured_info:
        query_parts.append("\nInformações estruturadas: " + " | ".join(structured_info))
    
    # Query final: texto completo + contexto estruturado
    query = "\n".join(query_parts) if query_parts else input_text or "buscar regras"
    
    # Buscar regras com metadados completos
    # Usar filtro por domínio se disponível para melhorar precisão da busca
    try:
        # Debug: imprimir query (pode remover depois)
        print(f"[DEBUG Knowledge] Query construída: {query}")
        print(f"[DEBUG Knowledge] Domínio identificado: {intent}")
        
        # Buscar com filtro por domínio (se intent estiver disponível e não for 'outros')
        # Filtrar por domínio melhora a precisão ao buscar apenas regras relevantes
        domain_filter = intent if intent and intent != "outros" else None
        
        # Extrair keywords das entidades para busca híbrida
        keywords = []
        if entities:
            if "procedimentos" in entities:
                procs = entities["procedimentos"]
                if isinstance(procs, list):
                    keywords.extend([str(p) for p in procs])
                else:
                    keywords.append(str(procs))
            if "medicacoes" in entities:
                meds = entities["medicacoes"]
                if isinstance(meds, list):
                    keywords.extend([str(m) for m in meds])
                else:
                    keywords.append(str(meds))
        
        # Usar busca híbrida se houver keywords, senão busca semântica simples
        if keywords:
            results = search_docs_hybrid(
                query=query,
                k=5,
                domain=domain_filter,
                keywords=keywords,
                semantic_weight=0.7  # 70% semântica, 30% keywords
            )
        else:
            results = search_docs_with_metadata(query, k=5, domain=domain_filter)
        
        print(f"[DEBUG Knowledge] Encontrados {len(results)} resultados")
        if domain_filter:
            print(f"[DEBUG Knowledge] Resultados filtrados por domínio: {domain_filter}")
        
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
                "domain": doc.metadata.get("domain", ""),  # Incluir domain nos metadados retornados
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
