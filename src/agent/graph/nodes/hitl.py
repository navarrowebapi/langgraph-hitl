
from langgraph.types import interrupt
from agent.graph.state import WorkflowState

def human_in_the_loop(state: WorkflowState) -> WorkflowState:
    decision = interrupt({
        "question": "Você aprova este pedido?",
        "context": state["retrieved_context"]
    })

    return {
        "human_decision": decision["approved"]
    }
