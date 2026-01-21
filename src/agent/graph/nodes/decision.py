from agent.graph.state import WorkflowState


def decide(state: WorkflowState) -> WorkflowState:
    """
    Analisa regras recuperadas e decide se requer aprovação humana (HITL).
    Usa regras do RAG ao invés de lógica hardcoded.
    """
    entities = state.get("entities", {})
    retrieved_rules = state.get("retrieved_rules", [])
    
    # Extrair valor total (pode estar em diferentes campos)
    valor_total = entities.get("valor_total") or entities.get("valor", 0)
    
    # Se não houver regras recuperadas, usar lógica padrão simples
    if not retrieved_rules:
        if valor_total > 500:
            decision = "hitl"
            decision_reasoning = f"Valor de R$ {valor_total} acima do limite padrão de R$ 500"
        else:
            decision = "auto"
            decision_reasoning = f"Valor de R$ {valor_total} dentro do limite para aprovação automática"
        
        return {
            "decision": decision,
            "decision_evidence": [],
            "decision_reasoning": decision_reasoning
        }
    
    # Analisar regras recuperadas
    # Usar todas as regras recuperadas (já foram filtradas pelo RAG por relevância)
    # Filtrar apenas regras com confiança mínima (> 0.3 para evitar ruído)
    relevant_rules = [
        r for r in retrieved_rules 
        if r.get("confidence", 0.0) > 0.3
    ]
    
    # Se não houver regras relevantes, usar todas
    if not relevant_rules:
        relevant_rules = retrieved_rules
    
    # Extrair threshold das regras
    # Priorizar regras de faturamento/aprovação sobre auditoria
    # Usar o MENOR threshold encontrado (mais restritivo = mais seguro)
    threshold = None  # None indica que ainda não encontramos threshold
    decision_evidence = []
    reasoning_parts = []
    
    import re
    
    # Separar regras por tipo para priorizar
    faturamento_rules = [r for r in relevant_rules if r.get("tipo_regra") == "faturamento"]
    auditoria_rules = [r for r in relevant_rules if r.get("tipo_regra") == "auditoria"]
    outras_rules = [r for r in relevant_rules if r.get("tipo_regra") not in ["faturamento", "auditoria"]]
    
    # Processar APENAS regras de faturamento e outras (NÃO auditoria)
    # Regras de auditoria são para valores maiores e não devem afetar o threshold de aprovação inicial
    for rule in faturamento_rules + outras_rules:
        rule_text = rule.get("text", "").lower()
        rule_id = rule.get("rule_id", "")
        tipo_regra = rule.get("tipo_regra", "")
        
        # Buscar padrões de valor nas regras de faturamento/aprovação
        if "acima de" in rule_text or "maior que" in rule_text or "superior a" in rule_text or "requerem aprovação" in rule_text or "requerem autorização" in rule_text:
            # Tentar extrair número da regra (buscar R$ seguido de número)
            # Buscar padrões como "R$ 500", "R$500", "R$ 1.000", etc
            numbers = re.findall(r'r\$\s*([\d.]+)', rule_text, re.IGNORECASE)
            if numbers:
                # Converter para int (remover pontos de milhar)
                for num_str in numbers:
                    try:
                        num_value = int(float(num_str.replace(".", "")))
                        # Sempre usar o MENOR threshold encontrado (mais restritivo = mais seguro)
                        if threshold is None:
                            threshold = num_value
                        else:
                            threshold = min(threshold, num_value)
                    except ValueError:
                        pass
        
        # Adicionar à evidência todas as regras relevantes (incluindo auditoria para rastreabilidade)
        if rule_id or rule.get("source"):
            if rule_id not in decision_evidence:
                decision_evidence.append(rule_id if rule_id else rule.get("source", ""))
                if len(reasoning_parts) < 3:  # Limitar a 3 regras na explicação
                    reasoning_parts.append(
                        f"Regra {rule_id or rule.get('source', '')}: {rule.get('text', '')[:80]}..."
                    )
    
    # Adicionar regras de auditoria à evidência (mas não ao threshold)
    for rule in auditoria_rules:
        rule_id = rule.get("rule_id", "")
        if rule_id or rule.get("source"):
            if rule_id not in decision_evidence:
                decision_evidence.append(rule_id if rule_id else rule.get("source", ""))
    
    # Se não encontrou threshold nas regras, usar padrão
    if threshold is None:
        threshold = 500
    
    # Decidir baseado no threshold encontrado nas regras
    if valor_total > threshold:
        decision = "hitl"
        decision_reasoning = (
            f"Valor de R$ {valor_total} acima do threshold de R$ {threshold} "
            f"conforme regras recuperadas. "
            + "; ".join(reasoning_parts[:2])  # Limitar a 2 regras na explicação
        )
    else:
        decision = "auto"
        decision_reasoning = (
            f"Valor de R$ {valor_total} dentro do limite de R$ {threshold} "
            f"para aprovação automática conforme regras."
        )
    
    return {
        "decision": decision,
        "decision_evidence": decision_evidence,
        "decision_reasoning": decision_reasoning
    }
