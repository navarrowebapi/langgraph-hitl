"""Script simples para testar o agente localmente."""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.graph import graph


async def main():
    """Testa o agente com um exemplo simples."""
    # Estado inicial
    inputs = {
        "changeme": "teste inicial"
    }
    
    # Configuração do contexto (opcional)
    config = {
        "my_configurable_param": "valor_configurado"
    }
    
    print("Executando o agente...")
    print(f"Input: {inputs}")
    print(f"Config: {config}\n")
    
    # Invoca o grafo
    result = await graph.ainvoke(inputs, config=config)
    
    print("Resultado:")
    print(f"   {result}")
    print(f"\nResposta: {result.get('changeme', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())

