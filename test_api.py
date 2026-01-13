"""
Script de teste para a API FastAPI
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Testa o endpoint de health check"""
    print("Testando health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_invoke():
    """Testa o endpoint de invocação do agente"""
    print("Testando invocação do agente...")
    payload = {
        "input_text": "Preciso fazer um pedido de compra no valor de R$ 600,00"
    }
    response = requests.post(
        f"{BASE_URL}/agent/invoke",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()

if __name__ == "__main__":
    try:
        test_health()
        test_invoke()
    except requests.exceptions.ConnectionError:
        print("Erro: Não foi possível conectar à API. Certifique-se de que ela está rodando.")
        print("Execute: docker-compose up -d")
    except Exception as e:
        print(f"Erro: {e}")
