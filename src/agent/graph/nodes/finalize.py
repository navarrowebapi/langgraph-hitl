from agent.graph.state import WorkflowState

def finalize(state: WorkflowState) -> WorkflowState:
    if state.get("human_decision") is False:
        return {"final_result": "Rejeitado"}

    return {"final_result": "Aprovado e processado"}
