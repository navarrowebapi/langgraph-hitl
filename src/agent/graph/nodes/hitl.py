from langgraph.types import interrupt
from agent.graph.state import WorkflowState


def human_in_the_loop(state: WorkflowState) -> WorkflowState:
    """
    Apresenta informações estruturadas ao humano para tomada de decisão.
    Inclui fatos, regras aplicadas, evidências e rastreabilidade.
    """
    # Preparar apresentação completa e estruturada
    user_id = state.get("user_id", "N/A")
    case_id = state.get("case_id", "N/A")
    entities = state.get("entities", {})
    retrieved_rules = state.get("retrieved_rules", [])
    decision_reasoning = state.get("decision_reasoning", "")
    
    # Extrair fatos estruturados
    fatos = {
        "procedimentos": entities.get("procedimentos", []),
        "valor_total": entities.get("valor_total") or entities.get("valor", 0),
        "plano": entities.get("plano", ""),
        "medicacoes": entities.get("medicacoes", []),
        "localidade": entities.get("localidade", ""),
    }
    
    # Formatar regras aplicadas
    # Usar todas as regras recuperadas (já foram filtradas pelo RAG)
    # Filtrar apenas regras com confiança mínima (> 0.3)
    regras_aplicadas = []
    source_of_truth = set()
    
    for rule in retrieved_rules:
        confidence = rule.get("confidence", 0.0)
        # Incluir todas as regras retornadas pelo RAG (são relevantes)
        # Filtrar apenas se confiança muito baixa (< 0.2)
        if confidence > 0.2:
            regras_aplicadas.append({
                "regra": rule.get("text", ""),
                "fonte": rule.get("source", ""),
                "secao": rule.get("section", ""),
                "linhas": rule.get("line_range", ""),
                "confianca": round(confidence, 2),
                "rule_id": rule.get("rule_id", ""),
            })
            source_of_truth.add(rule.get("source", ""))
    
    # Preparar apresentação para o interrupt
    presentation = {
        "user_id": user_id,
        "case_id": case_id,
        "question": f"Deve ser faturado o caso {case_id} para o usuário {user_id}?",
        
        # Dados estruturados (fatos)
        "fatos": fatos,
        
        # Evidências do RAG (regras aplicadas)
        "regras_aplicadas": regras_aplicadas,
        
        # Rastreabilidade (source of truth)
        "source_of_truth": list(source_of_truth),
        
        # Razão da decisão sugerida
        "razao": decision_reasoning,
        
        # Sugestão inicial baseada na decisão
        "sugestao": "Sim" if state.get("decision") == "hitl" else "Não",
        
        # Contexto completo (para compatibilidade)
        "context": state.get("retrieved_context", ""),
    }
    
    # Interrupt pausa a execução e retorna o valor quando continuamos
    decision = interrupt(presentation)
    
    # Processar resposta do humano
    if isinstance(decision, dict):
        approved = decision.get("approved", False)
        notes = decision.get("notes", "") or decision.get("human_notes", "")
    else:
        # Se for um valor simples (bool), usamos diretamente
        approved = bool(decision)
        notes = ""
    
    return {
        "human_decision": approved,
        "human_notes": notes
    }
