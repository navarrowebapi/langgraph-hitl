from langgraph.graph import StateGraph, END
from agent.graph.state import WorkflowState

from agent.graph.nodes import (
    interpretation,
    knowledge,
    decision,
    hitl,
    finalize
)

builder = StateGraph(WorkflowState)

builder.add_node("interpret", interpretation.interpret)
builder.add_node("knowledge", knowledge.retrieve_knowledge)
builder.add_node("decision", decision.decide)
builder.add_node("hitl", hitl.human_in_the_loop)
builder.add_node("finalize", finalize.finalize)

builder.set_entry_point("interpret")

builder.add_edge("interpret", "knowledge")
builder.add_edge("knowledge", "decision")

builder.add_conditional_edges(
    "decision",
    lambda s: "hitl" if s["decision"] == "hitl" else "finalize"
)

builder.add_edge("hitl", "finalize")
builder.add_edge("finalize", END)

graph = builder.compile()




# from typing import TypedDict
# from langgraph.graph import StateGraph, END
# from langgraph.types import interrupt
# from langchain_openai import ChatOpenAI

# # 1. Estado do grafo
# class AgentState(TypedDict):
#     user_input: str
#     approved: bool
#     result: str


# #llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# # Cria o modelo OpenAI
# model = ChatOpenAI(
#     model="gpt-3.5-turbo",
#     temperature=0.7
# )


# # 2. Nó que processa o texto do usuário
# def process_text(state: AgentState) -> AgentState:
#     response = model.invoke(
#         f"Reescreva o texto de forma mais clara:\n\n{state['user_input']}"
#     )

#     return {
#         "result": response.content
#     }


# # 3. Nó HITL: pede aprovação humana no Studio
# def human_approval(state: AgentState) -> AgentState:
#     decision = interrupt({
#         "question": "Você aprova o texto gerado?",
#         "generated_text": state["result"],
#         "instructions": "Responda com approved=true ou approved=false"
#     })

#     return {
#         "approved": decision.get("approved", False)
#     }


# # 4. Nó final
# def finalize(state: AgentState) -> AgentState:
#     if state["approved"]:
#         return {
#             "result": f"TEXTO FINAL APROVADO:\n{state['result']}"
#         }
#     else:
#         return {
#             "result": "Texto não aprovado pelo humano."
#         }


# # 5. Construção do grafo
# builder = StateGraph(AgentState)

# builder.add_node("process_text", process_text)
# builder.add_node("human_approval", human_approval)
# builder.add_node("finalize", finalize)

# builder.set_entry_point("process_text")
# builder.add_edge("process_text", "human_approval")
# builder.add_edge("human_approval", "finalize")
# builder.add_edge("finalize", END)

# graph = builder.compile()




