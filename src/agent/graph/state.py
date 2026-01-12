from typing import TypedDict, Literal

class WorkflowState(TypedDict):
    input_text: str
    intent: str
    entities: dict
    retrieved_context: str
    decision: Literal["auto", "hitl", "reject"]
    human_decision: bool | None
    final_result: str
