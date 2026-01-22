#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar a API do agente após ingestão de regras.
Uso: python test_api.py [número_do_teste]
"""

import requests
import json
import sys
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

API_URL = "http://localhost:8000/agent/invoke"

# Cores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.RESET}")

def test_endpoint(test_file):
    """Testa um endpoint com um arquivo JSON"""
    test_path = Path(test_file)
    
    if not test_path.exists():
        print_error(f"Arquivo não encontrado: {test_file}")
        return False
    
    print_header(f"Testando: {test_path.name}")
    
    # Carregar dados do teste
    with open(test_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print_info(f"Input: {data.get('input_text', 'N/A')[:80]}...")
    
    try:
        # Fazer requisição
        response = requests.post(API_URL, json=data, timeout=30)
        
        if response.status_code != 200:
            print_error(f"Erro HTTP {response.status_code}: {response.text}")
            return False
        
        result = response.json()
        
        # Verificar estrutura básica
        if 'result' not in result:
            print_error("Resposta não contém 'result'")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return False
        
        result_data = result['result']
        
        # Verificar domínio
        intent = result_data.get('intent', 'N/A')
        print_success(f"Domínio detectado: {intent}")
        
        # Verificar entidades
        entities = result_data.get('entities', {})
        if entities:
            print_info(f"Entidades extraídas: {list(entities.keys())}")
            if 'procedimentos' in entities:
                print(f"   - Procedimentos: {entities['procedimentos']}")
            if 'valor_total' in entities:
                print(f"   - Valor total: R$ {entities['valor_total']}")
        
        # Verificar regras recuperadas
        retrieved_rules = result_data.get('retrieved_rules', [])
        print_success(f"Regras encontradas: {len(retrieved_rules)}")
        
        if retrieved_rules:
            print("\n📚 Regras recuperadas:")
            for i, rule in enumerate(retrieved_rules[:3], 1):  # Mostrar apenas 3 primeiras
                rule_id = rule.get('rule_id', 'N/A')
                domain = rule.get('domain', 'N/A')
                confidence = rule.get('confidence', 0.0)
                print(f"   {i}. [{domain}] {rule_id} (confiança: {confidence:.2f})")
                if i < len(retrieved_rules):
                    print(f"      Texto: {rule.get('text', '')[:60]}...")
        
        # Verificar decisão
        decision = result_data.get('decision', 'N/A')
        requires_human = result.get('requires_human_decision', False)
        
        decision_color = Colors.YELLOW if decision == 'hitl' else Colors.GREEN
        print(f"\n{decision_color}Decisão: {decision.upper()}{Colors.RESET}")
        if requires_human:
            print_info("⚠️  Requer decisão humana (HITL)")
        
        # Verificar filtro por domínio
        if retrieved_rules:
            domains_found = set(r.get('domain', '') for r in retrieved_rules if r.get('domain'))
            if domains_found:
                print_info(f"Domínios nas regras: {', '.join(domains_found)}")
                if intent != 'outros' and intent in domains_found:
                    print_success("✅ Filtro por domínio funcionando!")
                elif intent == 'outros':
                    print_info("ℹ️  Domínio 'outros' não filtra regras")
        
        # Mostrar resultado final
        final_result = result_data.get('final_result_dict', {})
        if final_result:
            print(f"\n📋 Resultado final:")
            print(f"   - Deve ser faturado: {final_result.get('deve_ser_faturado', 'N/A')}")
            print(f"   - Precisa auditoria: {final_result.get('precisa_auditoria', 'N/A')}")
        
        print_success("Teste concluído com sucesso!")
        return True
        
    except requests.exceptions.ConnectionError:
        print_error(f"Não foi possível conectar à API em {API_URL}")
        print_info("Verifique se a API está rodando: uvicorn src.agent.api:app --reload")
        return False
    except Exception as e:
        print_error(f"Erro ao executar teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def list_tests():
    """Lista todos os arquivos de teste disponíveis"""
    test_files = sorted(Path('.').glob('test_*.json'))
    
    if not test_files:
        print_error("Nenhum arquivo de teste encontrado!")
        return
    
    print_header("Arquivos de teste disponíveis:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file.name}")
    
    print(f"\n{Colors.YELLOW}Uso: python test_api.py [número]{Colors.RESET}")
    print(f"{Colors.YELLOW}Exemplo: python test_api.py 1{Colors.RESET}")

def main():
    if len(sys.argv) > 1:
        test_num = sys.argv[1]
        
        # Tentar como número
        try:
            test_num_int = int(test_num)
            test_files = sorted(Path('.').glob('test_*.json'))
            if 1 <= test_num_int <= len(test_files):
                test_file = test_files[test_num_int - 1]
                success = test_endpoint(test_file)
                sys.exit(0 if success else 1)
            else:
                print_error(f"Número inválido. Use 1-{len(test_files)}")
                list_tests()
                sys.exit(1)
        except ValueError:
            # Tentar como nome de arquivo
            if test_num.endswith('.json'):
                test_file = test_num
            else:
                test_file = f"test_{test_num}.json"
            
            success = test_endpoint(test_file)
            sys.exit(0 if success else 1)
    else:
        # Executar todos os testes
        test_files = sorted(Path('.').glob('test_*.json'))
        
        if not test_files:
            print_error("Nenhum arquivo de teste encontrado!")
            print_info("Crie arquivos test_*.json ou use: python test_api.py --list")
            sys.exit(1)
        
        print_header(f"Executando {len(test_files)} testes...")
        
        results = []
        for test_file in test_files:
            success = test_endpoint(test_file)
            results.append((test_file.name, success))
            print()  # Linha em branco entre testes
        
        # Resumo
        print_header("Resumo dos Testes")
        passed = sum(1 for _, success in results if success)
        failed = len(results) - passed
        
        for test_name, success in results:
            status = f"{Colors.GREEN}✅ PASSOU{Colors.RESET}" if success else f"{Colors.RED}❌ FALHOU{Colors.RESET}"
            print(f"  {status} - {test_name}")
        
        print(f"\n{Colors.BOLD}Total: {passed}/{len(results)} testes passaram{Colors.RESET}")
        
        sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_tests()
    else:
        main()
