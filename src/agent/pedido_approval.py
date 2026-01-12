from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
import re

# 1. Estado do grafo
class OrderState(TypedDict):
    email_content: str
    pedido_id: str
    valor: float
    descricao: str
    status: Literal["pendente", "aprovado", "rejeitado"]
    aprovado: bool
    resultado: str


# Cria o modelo OpenAI
model = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)


# 2. E-mails simulados para teste
EMAILS_SIMULADOS = [
    """
    Assunto: Pedido de Compra #ORD-001
    
    Prezado Gerente,
    
    Solicitamos aprovação para o seguinte pedido:
    
    ID do Pedido: ORD-001
    Descrição: Equipamentos de escritório
    Valor: U$ 350.00
    
    Por favor, analise e aprove se necessário.
    
    Atenciosamente,
    Departamento de Compras
    """,
    """
    Assunto: Requisição de Aprovação - Pedido #ORD-002
    
    Olá,
    
    Temos um pedido que requer sua análise:
    
    Pedido ID: ORD-002
    Item: Licenças de software empresarial
    Valor Total: U$ 1,250.00
    
    Aguardamos sua aprovação.
    
    Obrigado,
    Equipe de TI
    """,
    """
    Assunto: Aprovação Necessária - ORD-003
    
    Caro Supervisor,
    
    Segue pedido para análise:
    
    ID: ORD-003
    Descrição: Mobiliário para nova sala de reuniões
    Valor: U$ 750.00
    
    Por favor, revise e aprove.
    
    Abraços,
    Departamento Administrativo
    """,
    """
    Assunto: Pedido #ORD-004 - Requer Aprovação
    
    Prezados,
    
    Pedido para análise:
    
    Número: ORD-004
    Descrição: Serviços de consultoria
    Valor: U$ 450.00
    
    Atenciosamente,
    RH
    """
]


# 3. Nó que extrai informações do e-mail
def parse_email(state: OrderState) -> OrderState:
    email = state["email_content"]
    
    # Extrai ID do pedido
    pedido_id_match = re.search(r'#?ORD-?\d+', email, re.IGNORECASE)
    pedido_id = pedido_id_match.group(0) if pedido_id_match else "DESCONHECIDO"
    
    # Extrai valor
    valor_match = re.search(r'U\$\s*([\d,]+\.?\d*)', email, re.IGNORECASE)
    if valor_match:
        valor_str = valor_match.group(1).replace(',', '')
        valor = float(valor_str)
    else:
        valor = 0.0
    
    # Extrai descrição usando LLM
    response = model.invoke(
        f"Extraia a descrição do pedido deste e-mail:\n\n{email}\n\n"
        "Responda apenas com a descrição do pedido, sem formatação."
    )
    descricao = response.content.strip()
    
    return {
        "pedido_id": pedido_id,
        "valor": valor,
        "descricao": descricao,
        "status": "pendente"
    }


# 4. Nó que verifica se precisa de aprovação HITL
def check_approval_needed(state: OrderState) -> OrderState:
    if state["valor"] > 500.0:
        return {"status": "pendente"}
    else:
        # Aprovação automática para valores <= 500
        return {
            "status": "aprovado",
            "aprovado": True,
            "resultado": f"Pedido {state['pedido_id']} aprovado automaticamente (valor: U$ {state['valor']:.2f})"
        }


# 5. Nó HITL: pede aprovação humana
def human_approval(state: OrderState) -> OrderState:
    decision = interrupt({
        "question": f"Você aprova o pedido {state['pedido_id']}?",
        "pedido_id": state["pedido_id"],
        "valor": state["valor"],
        "descricao": state["descricao"],
        "instructions": "Responda com approved=true ou approved=false"
    })
    
    aprovado = decision.get("approved", False)
    
    return {
        "aprovado": aprovado,
        "status": "aprovado" if aprovado else "rejeitado"
    }


# 6. Nó que atualiza o status do pedido
def update_order_status(state: OrderState) -> OrderState:
    if state["aprovado"]:
        return {
            "status": "aprovado",
            "resultado": f"Pedido {state['pedido_id']} APROVADO e atualizado no sistema.\n"
                        f"Valor: U$ {state['valor']:.2f}\n"
                        f"Descrição: {state['descricao']}"
        }
    else:
        return {
            "status": "rejeitado",
            "resultado": f"Pedido {state['pedido_id']} REJEITADO.\n"
                        f"Valor: U$ {state['valor']:.2f}\n"
                        f"Descrição: {state['descricao']}"
        }


# 7. Construção do grafo
builder = StateGraph(OrderState)

builder.add_node("parse_email", parse_email)
builder.add_node("check_approval_needed", check_approval_needed)
builder.add_node("human_approval", human_approval)
builder.add_node("update_order_status", update_order_status)

builder.set_entry_point("parse_email")
builder.add_edge("parse_email", "check_approval_needed")

# Condição: se valor > 500, vai para HITL, senão vai direto para atualização
builder.add_conditional_edges(
    "check_approval_needed",
    lambda state: "human_approval" if state["valor"] > 500.0 else "update_order_status"
)

builder.add_edge("human_approval", "update_order_status")
builder.add_edge("update_order_status", END)

graph = builder.compile()
