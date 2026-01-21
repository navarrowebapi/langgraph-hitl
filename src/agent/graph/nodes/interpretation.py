
from langchain_openai import ChatOpenAI
from agent.graph.state import WorkflowState
import json
import re


llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)

def interpret(state: WorkflowState) -> WorkflowState:
    """
    Extrai intenção e entidades do texto de entrada.
    Usa LLM para análise semântica e regex para extração de valores estruturados.
    """
    input_text = state.get("input_text", "")
    
    # Extrair user_id e case_id do input_text se presente
    user_id = state.get("user_id")
    case_id = state.get("case_id")
    
    # Tentar extrair user_id do texto se não estiver no estado
    if not user_id:
        user_match = re.search(r"User:\s*(\w+)", input_text, re.IGNORECASE)
        if user_match:
            user_id = user_match.group(1)
    
    # Tentar extrair case_id do texto se não estiver no estado
    # Buscar padrões como "case: CASE-123", "case CASE-123", "CASE-123", etc
    if not case_id:
        case_match = re.search(r"case[:\s]+([A-Z0-9\-]+)", input_text, re.IGNORECASE)
        if not case_match:
            # Tentar padrão direto como "CASE-2026-001"
            case_match = re.search(r"(CASE-[A-Z0-9\-]+)", input_text, re.IGNORECASE)
        if case_match:
            case_id = case_match.group(1)
    
    # Usar LLM para extrair intenção
    intent_prompt = f"""Analise o seguinte texto e identifique a intenção principal.
Opções: pode_faturar, quem_paga, precisa_auditoria, pedido_compra, outros.

Texto: {input_text}

Retorne APENAS a intenção, sem explicações:"""
    
    try:
        intent_response = llm.invoke(intent_prompt)
        intent = intent_response.content.strip().lower()
        # Normalizar intenção
        if "faturar" in intent or "faturamento" in intent:
            intent = "pode_faturar"
        elif "paga" in intent or "pagamento" in intent:
            intent = "quem_paga"
        elif "auditoria" in intent:
            intent = "precisa_auditoria"
        elif "pedido" in intent or "compra" in intent:
            intent = "pedido_compra"
        else:
            intent = "pode_faturar"  # Default
    except Exception:
        intent = "pode_faturar"  # Fallback
    
    # Extrair entidades usando regex e LLM
    entities = {}
    
    # Extrair procedimentos (códigos numéricos)
    procedimentos = re.findall(r"procedimento\s+(\d+)", input_text, re.IGNORECASE)
    if procedimentos:
        entities["procedimentos"] = procedimentos
    
    # Extrair valor total
    valor_match = re.search(r"valor\s+total\s+R\$\s*([\d.,]+)", input_text, re.IGNORECASE)
    if not valor_match:
        valor_match = re.search(r"R\$\s*([\d.,]+)", input_text)
    if valor_match:
        valor_str = valor_match.group(1).replace(".", "").replace(",", ".")
        try:
            entities["valor_total"] = float(valor_str)
        except ValueError:
            pass
    
    # Extrair medicamentos
    medicacoes = re.findall(r"medica[çc][õo]es?\s+([A-Z])", input_text, re.IGNORECASE)
    if not medicacoes:
        medicacoes = re.findall(r"medica[çc][õo]es?\s+([A-Za-z]+)", input_text, re.IGNORECASE)
    if medicacoes:
        entities["medicacoes"] = medicacoes
    
    # Extrair plano (se mencionado)
    plano_match = re.search(r"plano\s+(\w+)", input_text, re.IGNORECASE)
    if plano_match:
        entities["plano"] = plano_match.group(1).lower()
    
    # Extrair localidade (se mencionada)
    localidade_match = re.search(r"localidade[:\s]+(\w+)", input_text, re.IGNORECASE)
    if localidade_match:
        entities["localidade"] = localidade_match.group(1)
    
    # Se não encontrou valor_total mas encontrou apenas "valor", usar esse
    if "valor_total" not in entities and "valor" in entities:
        entities["valor_total"] = entities.pop("valor")
    
    result = {
        "intent": intent,
        "entities": entities,
    }
    
    # Adicionar user_id e case_id apenas se foram encontrados
    if user_id:
        result["user_id"] = user_id
    if case_id:
        result["case_id"] = case_id
    
    return result
