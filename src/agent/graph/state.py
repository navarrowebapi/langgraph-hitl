from typing import TypedDict, Literal, Optional

class WorkflowState(TypedDict):
    # Entrada
    input_text: str
    user_id: Optional[str]
    case_id: Optional[str]
    
    # Dados estruturados (do Interpret)
    intent: str
    entities: dict
    
    # RAG - Knowledge (regras recuperadas com metadados)
    retrieved_context: str  # Mantido para compatibilidade
    retrieved_rules: Optional[list[dict]]  # Lista de regras com metadados completos
    
    # Decision
    decision: Literal["auto", "hitl", "reject"]
    decision_evidence: Optional[list[str]]  # IDs das regras usadas
    decision_reasoning: Optional[str]  # Explicação da decisão
    
    # HITL
    human_decision: Optional[bool]
    human_notes: Optional[str]
    
    # Resultado final
    final_result: str  # Mantido como string para compatibilidade
    final_result_dict: Optional[dict]  # Resultado estruturado completo
