from agent.graph.state import WorkflowState


def finalize(state: WorkflowState) -> WorkflowState:
    """
    Finaliza o workflow e prepara resultado estruturado completo.
    Inclui decisão final, source of truth e rastreabilidade.
    """
    human_decision = state.get("human_decision")
    decision = state.get("decision", "auto")
    retrieved_rules = state.get("retrieved_rules", [])
    entities = state.get("entities", {})
    decision_reasoning = state.get("decision_reasoning", "")
    human_notes = state.get("human_notes", "")
    
    # Determinar resultado final
    if decision == "reject" or human_decision is False:
        deve_ser_faturado = False
        resultado_texto = "Rejeitado"
    elif decision == "auto" or human_decision is True:
        deve_ser_faturado = True
        resultado_texto = "Aprovado e processado"
    else:
        # Caso pendente ou indeciso
        deve_ser_faturado = None
        resultado_texto = "Pendente de decisão"
    
    # Extrair source of truth das regras (todas as regras recuperadas são relevantes)
    source_of_truth = list(set([
        rule.get("source", "") 
        for rule in retrieved_rules 
        if rule.get("source") and rule.get("confidence", 0.0) > 0.2
    ]))
    
    # Construir razão final
    razao_final = decision_reasoning or "Decisão baseada em regras recuperadas"
    if human_notes:
        razao_final += f" | Observações: {human_notes}"
    
    # Resultado estruturado completo
    final_result_dict = {
        "deve_ser_faturado": deve_ser_faturado,
        "quem_paga": entities.get("quem_paga", "operadora"),  # Pode vir das entidades
        "precisa_auditoria": decision == "hitl" or human_decision is False,
        "source_of_truth": source_of_truth,
        "razao": razao_final,
        "decision_evidence": state.get("decision_evidence", []),
        "user_id": state.get("user_id", ""),
        "case_id": state.get("case_id", ""),
    }
    
    return {
        "final_result": resultado_texto,
        "final_result_dict": final_result_dict
    }
