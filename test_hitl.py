"""
Script de teste para o fluxo HITL (Human-in-the-Loop)
Demonstra como usar os endpoints de HITL da API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_hitl_flow():
    """Testa o fluxo completo de HITL"""
    print("=" * 60)
    print("TESTE DO FLUXO HITL (Human-in-the-Loop)")
    print("=" * 60)
    print()
    
    # Passo 1: Invocar o agente
    print("1. Invocando o agente com pedido que requer aprovação...")
    print("-" * 60)
    
    payload = {
        "input_text": "Pedido de compra no valor de R$ 1200,00 para equipamentos de TI"
    }
    
    response = requests.post(
        f"{BASE_URL}/agent/invoke",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"📋 Thread ID: {result.get('thread_id')}")
    print(f"🤔 Requer decisão humana: {result.get('requires_human_decision')}")
    
    if result.get('interrupt_info'):
        print(f"📝 Pergunta: {result['interrupt_info'].get('question')}")
        print(f"📄 Contexto: {result['interrupt_info'].get('context', 'N/A')}")
    
    print()
    
    # Verificar se há interrupt
    if not result.get('requires_human_decision'):
        print("⚠️  Não há interrupt pendente. O fluxo foi concluído automaticamente.")
        print(json.dumps(result['result'], indent=2, ensure_ascii=False))
        return
    
    thread_id = result.get('thread_id')
    if not thread_id:
        print("❌ Thread ID não encontrado na resposta")
        return
    
    # Passo 2: Consultar estado do thread (opcional)
    print("2. Consultando estado do thread...")
    print("-" * 60)
    
    state_response = requests.get(f"{BASE_URL}/agent/thread/{thread_id}/state")
    if state_response.status_code == 200:
        state = state_response.json()
        print(f"✅ Estado obtido")
        print(f"   Tem interrupt: {state.get('has_interrupt')}")
        print(f"   Próximos passos: {state.get('next', [])}")
    else:
        print(f"⚠️  Não foi possível obter o estado: {state_response.status_code}")
    
    print()
    
    # Passo 3: Simular decisão humana (aprovar)
    print("3. Enviando decisão humana (APROVAR)...")
    print("-" * 60)
    
    decision_payload = {
        "thread_id": thread_id,
        "approved": True
    }
    
    decision_response = requests.post(
        f"{BASE_URL}/agent/hitl/decide",
        json=decision_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if decision_response.status_code != 200:
        print(f"❌ Erro: {decision_response.status_code}")
        print(decision_response.text)
        return
    
    decision_result = decision_response.json()
    print(f"✅ Status: {decision_response.status_code}")
    print(f"📋 Thread ID: {decision_result.get('thread_id')}")
    print(f"🤔 Ainda requer decisão: {decision_result.get('requires_human_decision')}")
    
    print()
    print("📊 Resultado Final:")
    print("-" * 60)
    print(json.dumps(decision_result['result'], indent=2, ensure_ascii=False))
    
    print()
    print("=" * 60)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 60)


def test_hitl_reject():
    """Testa o fluxo de HITL com rejeição"""
    print("\n" + "=" * 60)
    print("TESTE DO FLUXO HITL COM REJEIÇÃO")
    print("=" * 60)
    print()
    
    # Passo 1: Invocar o agente
    print("1. Invocando o agente...")
    payload = {
        "input_text": "Pedido de compra no valor de R$ 800,00"
    }
    
    response = requests.post(
        f"{BASE_URL}/agent/invoke",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.status_code}")
        return
    
    result = response.json()
    thread_id = result.get('thread_id')
    
    if not result.get('requires_human_decision'):
        print("⚠️  Não há interrupt. Testando com rejeição direta...")
        return
    
    # Passo 2: Rejeitar
    print("2. Enviando decisão de REJEIÇÃO...")
    decision_payload = {
        "thread_id": thread_id,
        "approved": False
    }
    
    decision_response = requests.post(
        f"{BASE_URL}/agent/hitl/decide",
        json=decision_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if decision_response.status_code == 200:
        decision_result = decision_response.json()
        print("✅ Rejeição processada")
        print(f"📊 Resultado: {decision_result['result'].get('final_result', 'N/A')}")
    else:
        print(f"❌ Erro: {decision_response.status_code}")


if __name__ == "__main__":
    try:
        # Verificar se a API está rodando
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ API não está respondendo. Certifique-se de que está rodando.")
            print(f"   Execute: docker-compose up -d")
            exit(1)
        
        # Teste principal
        test_hitl_flow()
        
        # Teste com rejeição
        test_hitl_reject()
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API.")
        print("   Certifique-se de que a API está rodando:")
        print("   docker-compose up -d")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
