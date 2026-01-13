"""
API FastAPI para expor o grafo LangGraph
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
import uuid

# Adicionar o diretório src ao path se necessário
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agent.graph.graph import builder
from agent.graph.state import WorkflowState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# Configurar checkpoint para manter estado entre execuções (necessário para HITL)
memory = MemorySaver()
# Compilar o grafo com checkpoint (o builder ainda não foi compilado)
graph_with_checkpoint = builder.compile(checkpointer=memory)

app = FastAPI(
    title="LangGraph Agent API",
    description="API para interagir com o agente LangGraph",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    """Modelo de requisição para o agente"""
    input_text: str
    config: Optional[dict] = None
    thread_id: Optional[str] = None  # ID do thread para continuar execução


class HumanDecisionRequest(BaseModel):
    """Modelo para decisão humana no HITL"""
    thread_id: str
    approved: bool
    interrupt_id: Optional[str] = None  # ID do interrupt específico (opcional)


class AgentResponse(BaseModel):
    """Modelo de resposta do agente"""
    result: dict
    status: str = "success"
    thread_id: Optional[str] = None
    requires_human_decision: bool = False
    interrupt_info: Optional[dict] = None


class HealthResponse(BaseModel):
    """Resposta de health check"""
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
async def root():
    """Endpoint raiz - health check"""
    return HealthResponse(
        status="ok",
        message="LangGraph Agent API está rodando"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        message="API está saudável"
    )


@app.post("/agent/invoke", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """
    Invoca o grafo do agente com o texto de entrada
    
    Args:
        request: Requisição contendo input_text, config opcional e thread_id opcional
        
    Returns:
        Resposta com o resultado da execução do grafo
        Se houver interrupt (HITL), requires_human_decision será True
    """
    try:
        # Gerar ou usar thread_id fornecido
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # Preparar o estado inicial
        initial_state: WorkflowState = {
            "input_text": request.input_text,
            "intent": "",
            "entities": {},
            "retrieved_context": "",
            "decision": "auto",
            "human_decision": None,
            "final_result": ""
        }
        
        # Configuração com thread_id para checkpoint
        config = request.config or {}
        config["configurable"] = {"thread_id": thread_id}
        
        # Invocar o grafo com checkpoint (necessário para HITL)
        result = await graph_with_checkpoint.ainvoke(initial_state, config=config)
        
        # Verificar se há interrupt (HITL)
        interrupt_info = None
        requires_human = False
        
        if "__interrupt__" in result:
            requires_human = True
            interrupts = result["__interrupt__"]
            if interrupts and len(interrupts) > 0:
                # interrupts[0] é um objeto Interrupt, não um dicionário
                interrupt_obj = interrupts[0]
                # Acessar o valor do interrupt usando o atributo .value
                if hasattr(interrupt_obj, 'value'):
                    interrupt_info = interrupt_obj.value if isinstance(interrupt_obj.value, dict) else {"value": interrupt_obj.value}
                else:
                    # Se não tiver atributo value, tentar como dicionário
                    interrupt_info = interrupt_obj if isinstance(interrupt_obj, dict) else {}
                
                # Adicionar o ID do interrupt se disponível
                if hasattr(interrupt_obj, 'id'):
                    interrupt_info["interrupt_id"] = interrupt_obj.id
                elif isinstance(interrupt_obj, dict) and "id" in interrupt_obj:
                    interrupt_info["interrupt_id"] = interrupt_obj["id"]
        
        return AgentResponse(
            result=result,
            status="success",
            thread_id=thread_id,
            requires_human_decision=requires_human,
            interrupt_info=interrupt_info
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar o agente: {str(e)}"
        )


@app.post("/agent/stream")
async def stream_agent(request: AgentRequest):
    """
    Stream de eventos do grafo do agente
    
    Args:
        request: Requisição contendo input_text, config opcional e thread_id opcional
        
    Yields:
        Eventos do grafo em tempo real
    """
    try:
        # Gerar ou usar thread_id fornecido
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # Preparar o estado inicial
        initial_state: WorkflowState = {
            "input_text": request.input_text,
            "intent": "",
            "entities": {},
            "retrieved_context": "",
            "decision": "auto",
            "human_decision": None,
            "final_result": ""
        }
        
        # Configuração com thread_id para checkpoint
        config = request.config or {}
        config["configurable"] = {"thread_id": thread_id}
        
        # Stream do grafo com checkpoint
        async for event in graph_with_checkpoint.astream(initial_state, config=config):
            yield {
                "event": event,
                "status": "streaming",
                "thread_id": thread_id
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar stream do agente: {str(e)}"
        )


@app.post("/agent/hitl/decide", response_model=AgentResponse)
async def human_decision(request: HumanDecisionRequest):
    """
    Processa a decisão humana e continua a execução do grafo após um interrupt (HITL)
    
    Args:
        request: Requisição contendo thread_id, approved e interrupt_id opcional
        
    Returns:
        Resposta com o resultado final da execução após a decisão humana
        Se ainda houver outro interrupt, requires_human_decision será True novamente
        
    Exemplo:
        POST /agent/hitl/decide
        {
            "thread_id": "abc-123",
            "approved": true
        }
    """
    try:
        # Configuração com thread_id
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # Obter o estado atual do checkpoint
        state = await graph_with_checkpoint.aget_state(config)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {request.thread_id} não encontrado"
            )
        
        # Verificar se há interrupt pendente
        # O LangGraph armazena interrupts em state.tasks quando há checkpoint
        # state.tasks é uma lista de tarefas/interrupts pendentes
        has_interrupt = False
        
        # Verificar em state.tasks (onde o LangGraph armazena interrupts pendentes)
        if hasattr(state, 'tasks') and state.tasks and len(state.tasks) > 0:
            has_interrupt = True
        # Verificar em state.values["__interrupt__"] (formato retornado pelo ainvoke)
        elif state.values and state.values.get("__interrupt__"):
            has_interrupt = True
        # Verificar se está aguardando HITL (inferência baseada no estado do workflow)
        else:
            state_values = state.values if state.values else {}
            next_nodes = state.next if hasattr(state, 'next') else []
            # Se o próximo nó é "hitl" e human_decision é None, há um interrupt pendente
            is_waiting_for_hitl = (
                "hitl" in next_nodes and 
                state_values.get("human_decision") is None and
                state_values.get("decision") == "hitl"
            )
            has_interrupt = is_waiting_for_hitl
        
        if not has_interrupt:
            raise HTTPException(
                status_code=400,
                detail="Não há interrupt pendente para este thread"
            )
        
        # Para continuar após um interrupt, precisamos usar Command com resume
        # O valor passado em resume se torna o retorno do interrupt()
        decision_value = {"approved": request.approved}
        
        # Continuar a execução usando Command
        result = await graph_with_checkpoint.ainvoke(
            Command(resume=decision_value),
            config=config
        )
        
        # Verificar se ainda há interrupt (pode haver múltiplos em workflows complexos)
        interrupt_info = None
        requires_human = False
        
        if "__interrupt__" in result:
            requires_human = True
            interrupts = result["__interrupt__"]
            if interrupts and len(interrupts) > 0:
                # interrupts[0] é um objeto Interrupt, não um dicionário
                interrupt_obj = interrupts[0]
                # Acessar o valor do interrupt usando o atributo .value
                if hasattr(interrupt_obj, 'value'):
                    interrupt_info = interrupt_obj.value if isinstance(interrupt_obj.value, dict) else {"value": interrupt_obj.value}
                else:
                    interrupt_info = interrupt_obj if isinstance(interrupt_obj, dict) else {}
                
                # Adicionar o ID do interrupt se disponível
                if hasattr(interrupt_obj, 'id'):
                    interrupt_info["interrupt_id"] = interrupt_obj.id
                elif isinstance(interrupt_obj, dict) and "id" in interrupt_obj:
                    interrupt_info["interrupt_id"] = interrupt_obj["id"]
        
        return AgentResponse(
            result=result,
            status="success",
            thread_id=request.thread_id,
            requires_human_decision=requires_human,
            interrupt_info=interrupt_info
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar decisão humana: {str(e)}"
        )


@app.get("/agent/thread/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """
    Obtém o estado atual de um thread
    
    Útil para verificar o estado de uma execução que está aguardando decisão humana
    
    Args:
        thread_id: ID do thread
        
    Returns:
        Estado atual do thread incluindo valores e próximos passos
        
    Exemplo:
        GET /agent/thread/abc-123/state
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph_with_checkpoint.aget_state(config)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} não encontrado"
            )
        
        # Preparar resposta com informações úteis
        next_nodes = state.next if hasattr(state, 'next') else []
        
        # Verificar se há interrupt pendente
        # O interrupt pode estar em state.values["__interrupt__"] OU
        # podemos inferir que há interrupt se:
        # 1. O próximo nó é "hitl" E human_decision é None
        # 2. Ou se há __interrupt__ em state.values
        has_interrupt_in_values = "__interrupt__" in state.values if state.values else False
        
        # Verificar se há interrupt baseado no estado do workflow
        # Se o próximo nó é "hitl" e human_decision é None, há um interrupt pendente
        state_values = state.values if state.values else {}
        is_waiting_for_hitl = (
            "hitl" in next_nodes and 
            state_values.get("human_decision") is None and
            state_values.get("decision") == "hitl"
        )
        
        has_interrupt = has_interrupt_in_values or is_waiting_for_hitl
        
        response = {
            "thread_id": thread_id,
            "state": state_values,
            "next": next_nodes,
            "has_interrupt": has_interrupt
        }
        
        # Se houver interrupt, incluir informações
        if has_interrupt:
            # Primeiro tentar obter do state.values
            if has_interrupt_in_values:
                interrupts = state.values.get("__interrupt__", [])
                if interrupts:
                    interrupt_obj = interrupts[0]
                    # Acessar o valor do interrupt usando o atributo .value
                    if hasattr(interrupt_obj, 'value'):
                        response["interrupt_info"] = interrupt_obj.value if isinstance(interrupt_obj.value, dict) else {"value": interrupt_obj.value}
                    else:
                        response["interrupt_info"] = interrupt_obj if isinstance(interrupt_obj, dict) else {}
                    
                    # Adicionar o ID do interrupt se disponível
                    if hasattr(interrupt_obj, 'id'):
                        response["interrupt_id"] = interrupt_obj.id
                    elif isinstance(interrupt_obj, dict) and "id" in interrupt_obj:
                        response["interrupt_id"] = interrupt_obj["id"]
            elif is_waiting_for_hitl:
                # Se inferimos que há interrupt pelo estado, criar informações básicas
                response["interrupt_info"] = {
                    "question": "Você aprova este pedido?",
                    "context": state_values.get("retrieved_context", "")
                }
                response["interrupt_reason"] = "Aguardando decisão humana no nó HITL"
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter estado do thread: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
