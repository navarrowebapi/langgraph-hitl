"""
API FastAPI para expor o grafo LangGraph
"""
from contextlib import asynccontextmanager
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

from agent.audit import insert_event, setup_audit_tables, upsert_request
from agent.graph.graph import builder
from agent.graph.state import WorkflowState
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

def _build_postgres_uri() -> str:
    """Obtém a URI do Postgres a partir do ambiente."""
    direct_uri = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if not direct_uri:
        raise RuntimeError(
            "POSTGRES_URL/DATABASE_URL não configurado. "
            "Defina a URI completa do banco no ambiente."
        )
    return direct_uri


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o checkpointer Postgres e compila o grafo."""
    db_uri = _build_postgres_uri()
    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        await checkpointer.setup()
        app.state.graph = builder.compile(checkpointer=checkpointer)
        app.state.db_uri = db_uri
        await setup_audit_tables(db_uri)
        yield

app = FastAPI(
    title="LangGraph Agent API",
    description="API para interagir com o agente LangGraph",
    version="1.0.0",
    lifespan=lifespan,
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
    requester_id: Optional[str] = None


class HumanDecisionRequest(BaseModel):
    """Modelo para decisão humana no HITL"""
    thread_id: str
    approved: bool
    interrupt_id: Optional[str] = None  # ID do interrupt específico (opcional)
    notes: Optional[str] = None  # Observações do humano (opcional)


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


def _get_graph():
    graph = getattr(app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="Grafo não inicializado. Verifique a conexão com o Postgres."
        )
    return graph


def _get_db_uri():
    db_uri = getattr(app.state, "db_uri", None)
    if not db_uri:
        raise HTTPException(
            status_code=503,
            detail="Banco de auditoria não inicializado. Verifique o Postgres."
        )
    return db_uri


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
            "user_id": None,
            "case_id": None,
            "intent": "",
            "entities": {},
            "retrieved_context": "",
            "retrieved_rules": None,
            "decision": "auto",
            "decision_evidence": None,
            "decision_reasoning": None,
            "human_decision": None,
            "human_notes": None,
            "final_result": "",
            "final_result_dict": None
        }
        
        # Configuração com thread_id para checkpoint
        config = request.config or {}
        config["configurable"] = {"thread_id": thread_id}

        db_uri = _get_db_uri()
        await upsert_request(
            db_uri=db_uri,
            thread_id=thread_id,
            requester_id=request.requester_id,
            input_text=request.input_text,
            status="started",
            last_node="interpret",
        )
        await insert_event(
            db_uri=db_uri,
            thread_id=thread_id,
            event_type="invoke",
            payload={"input_text": request.input_text},
        )

        graph = _get_graph()
        result = await graph.ainvoke(initial_state, config=config)
        
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
        
        status = "hitl_pending" if requires_human else "completed"
        last_node = "hitl" if requires_human else "finalize"
        await upsert_request(
            db_uri=db_uri,
            thread_id=thread_id,
            requester_id=request.requester_id,
            input_text=request.input_text,
            status=status,
            last_node=last_node,
        )
        await insert_event(
            db_uri=db_uri,
            thread_id=thread_id,
            event_type="invoke_complete",
            payload={"requires_human_decision": requires_human},
        )

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
            "user_id": None,
            "case_id": None,
            "intent": "",
            "entities": {},
            "retrieved_context": "",
            "retrieved_rules": None,
            "decision": "auto",
            "decision_evidence": None,
            "decision_reasoning": None,
            "human_decision": None,
            "human_notes": None,
            "final_result": "",
            "final_result_dict": None
        }
        
        # Configuração com thread_id para checkpoint
        config = request.config or {}
        config["configurable"] = {"thread_id": thread_id}

        graph = _get_graph()
        async for event in graph.astream(initial_state, config=config):
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

        db_uri = _get_db_uri()
        await upsert_request(
            db_uri=db_uri,
            thread_id=request.thread_id,
            requester_id=None,
            input_text=None,
            status="hitl_pending",
            last_node="hitl",
        )
        await insert_event(
            db_uri=db_uri,
            thread_id=request.thread_id,
            event_type="hitl_decide",
            payload={"approved": request.approved},
        )
        
        # Obter o estado atual do checkpoint
        graph = _get_graph()
        state = await graph.aget_state(config)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {request.thread_id} não encontrado"
            )
        
        # Verificar se há interrupt pendente
        # O LangGraph com checkpoint armazena interrupts de várias formas
        has_interrupt = False
        interrupt_details = []
        
        state_values = state.values if state.values else {}
        next_nodes = state.next if hasattr(state, 'next') else []
        
        # Método 1: Verificar em state.tasks (onde o LangGraph armazena interrupts pendentes)
        if hasattr(state, 'tasks') and state.tasks and len(state.tasks) > 0:
            has_interrupt = True
            interrupt_details.append(f"Encontrado em state.tasks: {len(state.tasks)} tarefas")
        
        # Método 2: Verificar em state.values["__interrupt__"] (formato retornado pelo ainvoke)
        elif state_values.get("__interrupt__"):
            has_interrupt = True
            interrupt_details.append("Encontrado em state.values['__interrupt__']")
        
        # Método 3: Verificar se está aguardando HITL (inferência baseada no estado do workflow)
        # Se o próximo nó é "hitl" e human_decision é None, há um interrupt pendente
        elif "hitl" in next_nodes and state_values.get("human_decision") is None and state_values.get("decision") == "hitl":
            has_interrupt = True
            interrupt_details.append("Inferido: próximo nó é 'hitl' e human_decision é None")
        
        # Método 4: Verificar se há tasks pendentes usando get_state com include_next
        if not has_interrupt:
            try:
                # Tentar obter estado com mais detalhes
                detailed_state = await graph.aget_state(config, include_next=["hitl"])
                if detailed_state and hasattr(detailed_state, 'tasks') and detailed_state.tasks:
                    has_interrupt = True
                    interrupt_details.append("Encontrado via get_state com include_next")
            except Exception:
                pass
        
        # Se ainda não encontrou, verificar se o estado indica que está no nó hitl
        if not has_interrupt:
            # Se decision é "hitl" e human_decision é None, assumir que há interrupt
            if state_values.get("decision") == "hitl" and state_values.get("human_decision") is None:
                has_interrupt = True
                interrupt_details.append("Inferido: decision='hitl' e human_decision=None")
        
        if not has_interrupt:
            # Retornar informações de debug úteis
            debug_info = {
                "thread_id": request.thread_id,
                "has_tasks": hasattr(state, 'tasks') and bool(state.tasks) if hasattr(state, 'tasks') else False,
                "has_interrupt_in_values": bool(state_values.get("__interrupt__")),
                "next_nodes": list(next_nodes) if next_nodes else [],
                "decision": state_values.get("decision"),
                "human_decision": state_values.get("human_decision"),
                "state_keys": list(state_values.keys()) if state_values else []
            }
            raise HTTPException(
                status_code=400,
                detail=f"Não há interrupt pendente para este thread. Debug: {debug_info}"
            )
        
        # Para continuar após um interrupt, precisamos usar Command com resume
        # O valor passado em resume se torna o retorno do interrupt()
        # Incluir notes se fornecido
        decision_value = {"approved": request.approved}
        if hasattr(request, 'notes') and request.notes:
            decision_value["notes"] = request.notes
        
        # Continuar a execução usando Command
        # Com checkpoint, o Command resume o interrupt pendente
        result = await graph.ainvoke(
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

        status = "hitl_pending" if requires_human else "completed"
        last_node = "hitl" if requires_human else "finalize"
        await upsert_request(
            db_uri=db_uri,
            thread_id=request.thread_id,
            requester_id=None,
            input_text=None,
            status=status,
            last_node=last_node,
        )
        await insert_event(
            db_uri=db_uri,
            thread_id=request.thread_id,
            event_type="resume_complete",
            payload={"requires_human_decision": requires_human},
        )
        
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
        graph = _get_graph()
        state = await graph.aget_state(config)
        
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
