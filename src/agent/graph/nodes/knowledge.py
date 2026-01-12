from agent.graph.state import WorkflowState
from agent.rag.qdrant import search_docs

def retrieve_knowledge(state: WorkflowState) -> WorkflowState:
    return {"retrieved_context": "Teste de contexto"}
    # context = search_docs(state["input_text"])

    # return {
    #     "retrieved_context": context
    # }
