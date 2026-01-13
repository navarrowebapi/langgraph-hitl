
from langgraph.types import interrupt
from agent.graph.state import WorkflowState

def human_in_the_loop(state: WorkflowState) -> WorkflowState:
    # Interrupt pausa a execução e retorna o valor quando continuamos
    decision = interrupt({
        "question": "Você aprova este pedido?",
        "context": state["retrieved_context"]
    })
    
    # Quando continuamos após o interrupt, 'decision' será o valor passado no Command
    # Se for um dicionário, acessamos diretamente; se for um valor simples, tratamos adequadamente
    if isinstance(decision, dict):
        approved = decision.get("approved", False)
    else:
        # Se for um valor simples (bool), usamos diretamente
        approved = bool(decision)

    return {
        "human_decision": approved
    }
