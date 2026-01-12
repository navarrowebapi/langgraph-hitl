from agent.graph.state import WorkflowState

def decide(state: WorkflowState) -> WorkflowState:
    valor = state["entities"].get("valor", 0)

    if valor > 500:
        decision = "hitl"
    else:
        decision = "auto"

    return {"decision": decision}
