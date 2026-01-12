# Como Testar/Rodar o Agente LangGraph

Existem várias formas de testar e rodar seu agente. Aqui estão as principais:

## 1. Script Python Simples (Mais Rápido)

Use o arquivo `test_agent.py` que foi criado:

```bash
python test_agent.py
```

Este script executa o agente diretamente e mostra o resultado.

## 2. Usando LangGraph Dev Server (Recomendado)

O LangGraph CLI permite rodar um servidor local com interface visual:

```bash
langgraph dev
```

Isso vai:
- Iniciar um servidor local na porta padrão
- Abrir o LangGraph Studio (interface visual)
- Permitir testar o agente através da interface web
- Hot reload automático quando você modificar o código

**Nota:** Se houver problemas de encoding no Windows, você pode precisar configurar a variável de ambiente:
```powershell
$env:PYTHONIOENCODING="utf-8"
langgraph dev
```

## 3. Rodar os Testes Existentes

O projeto já tem testes configurados:

```bash
# Rodar todos os testes
pytest

# Rodar apenas testes de integração
pytest tests/integration_tests/

# Rodar apenas testes unitários
pytest tests/unit_tests/
```

## 4. Teste Direto no Python (REPL)

Você pode testar diretamente no Python interativo:

```python
import asyncio
import sys
sys.path.insert(0, 'src')

from agent.graph import graph

# Teste simples
async def test():
    result = await graph.ainvoke({"changeme": "teste"})
    print(result)

asyncio.run(test())
```

## 5. Criar um Script Personalizado

Você pode criar seu próprio script de teste em `test_agent.py` ou criar novos scripts:

```python
import asyncio
import sys
sys.path.insert(0, 'src')

from agent.graph import graph

async def main():
    # Seu código de teste aqui
    inputs = {"changeme": "seu valor"}
    config = {"my_configurable_param": "seu parametro"}
    result = await graph.ainvoke(inputs, config=config)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Estrutura do Estado e Configuração

### Estado (State)
O estado inicial deve conter:
- `changeme`: string (valor inicial)

### Configuração (Context)
Você pode passar configurações opcionais:
- `my_configurable_param`: string (parâmetro configurável)

### Exemplo Completo

```python
import asyncio
from agent.graph import graph

async def exemplo():
    # Estado inicial
    inputs = {
        "changeme": "valor inicial"
    }
    
    # Configuração opcional
    config = {
        "my_configurable_param": "meu valor"
    }
    
    # Executa o grafo
    resultado = await graph.ainvoke(inputs, config=config)
    print(resultado)

asyncio.run(exemplo())
```

## Próximos Passos

1. **Modificar o agente**: Edite `src/agent/graph.py` para adicionar lógica personalizada
2. **Adicionar modelo OpenAI**: Integre um modelo LLM usando `langchain-openai`
3. **Adicionar mais nós**: Crie um fluxo mais complexo com múltiplos nós
4. **Usar LangGraph Studio**: Use `langgraph dev` para visualizar e debugar seu grafo

