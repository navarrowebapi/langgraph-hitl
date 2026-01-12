
from langchain_openai import ChatOpenAI
from agent.graph.state import WorkflowState


llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)

def interpret(state: WorkflowState) -> WorkflowState:
    response = llm.invoke(
        f"Analise o texto e retorne intenção e entidades:\n{state['input_text']}"
    )

    return {
        "intent": "pedido_compra",
        "entities": {"valor": 1200}
    }
