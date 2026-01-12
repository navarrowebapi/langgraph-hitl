"""LangGraph agent com OpenAI.

Agente conversacional que usa OpenAI para responder mensagens.
"""

from __future__ import annotations

from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessageGraph
from langgraph.graph.message import add_messages

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


async def call_model(messages: Annotated[list[BaseMessage], add_messages]):
    """Chama o modelo OpenAI para gerar uma resposta.
    
    Args:
        messages: Lista de mensagens do histórico da conversa
        
    Returns:
        Mensagem de resposta do modelo
    """
    # Cria o modelo OpenAI
    model = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7
    )
    
    # Invoca o modelo com todas as mensagens
    response = await model.ainvoke(messages)
    
    return response


# Define o grafo
graph = (
    MessageGraph()
    .add_node("chat", call_model)
    .add_edge("__start__", "chat")
    .compile(name="OpenAI Chat Agent")
)