
from langchain_openai import ChatOpenAI
from agent.graph.state import WorkflowState
import json
import re


llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)

# Domínios disponíveis para Domain Routing
AVAILABLE_DOMAINS = [
    "faturamento",
    "juridico",
    "planos_e_cobertura",
    "cadastro",
    "atendimento",
    "outros"
]

# Regras determinísticas para descoberta rápida de domínio
DOMAIN_RULES = {
    "planos_e_cobertura": [
        "plano", "planos", "cobertura", "coberturas", "benefício", "benefícios",
        "tabela", "tabelas", "procedimento coberto", "procedimentos cobertos"
    ],
    "faturamento": [
        "valor", "valores", "emitir", "faturar", "faturamento", "fatura",
        "nota fiscal", "nf", "cobrança", "cobrar", "pagamento", "pagar"
    ],
    "atendimento": [
        "reclamação", "reclamações", "contestar", "contestação", "solicitação",
        "solicitações", "dúvida", "dúvidas", "atendimento", "suporte",
        "problema", "problemas", "queixa", "queixas"
    ],
    "juridico": [
        "jurídico", "legal", "lei", "leis", "contrato", "contratos",
        "processo", "processos", "ação judicial", "advogado", "advogados"
    ],
    "cadastro": [
        "cadastro", "cadastrar", "dados pessoais", "informações pessoais",
        "alterar cadastro", "atualizar cadastro", "cpf", "rg", "endereço"
    ]
}

def _detect_domain_deterministic(text: str) -> str:
    """
    Detecta o domínio usando regras determinísticas baseadas em palavras-chave.
    Retorna o domínio mais provável ou 'outros' se nenhum padrão for encontrado.
    
    Usa scoring ponderado: palavras-chave mais específicas têm maior peso.
    """
    text_lower = text.lower()
    
    # Contar ocorrências de palavras-chave por domínio
    domain_scores = {}
    
    for domain, keywords in DOMAIN_RULES.items():
        score = 0
        for keyword in keywords:
            # Verificar se a palavra-chave está presente no texto
            # Priorizar palavras completas sobre substrings
            if keyword in text_lower:
                # Palavras-chave mais longas (mais específicas) têm maior peso
                weight = len(keyword.split())  # Multi-word phrases têm mais peso
                score += weight
        
        if score > 0:
            domain_scores[domain] = score
    
    # Retornar domínio com maior score
    if domain_scores:
        # Ordenar por score (maior primeiro)
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        best_domain = sorted_domains[0][0]
        best_score = sorted_domains[0][1]
        
        # Debug: mostrar detecção determinística
        print(f"[DEBUG Interpretation] Detecção determinística: {best_domain} (score: {best_score})")
        
        return best_domain
    
    # Se nenhum padrão encontrado, retornar 'outros'
    print(f"[DEBUG Interpretation] Nenhum padrão encontrado, usando domínio: outros")
    return "outros"


def _refine_domain_with_llm(text: str, suggested_domain: str) -> str:
    """
    Usa LLM para validar e refinar a classificação de domínio sugerida pelas regras determinísticas.
    """
    domains_list = ", ".join(AVAILABLE_DOMAINS)
    
    intent_prompt = f"""Analise o seguinte texto e identifique o domínio/área mais apropriada.
    
Domínios disponíveis: {domains_list}

Texto: {text}

Sugestão inicial (baseada em regras): {suggested_domain}

Retorne APENAS o nome do domínio mais apropriado, sem explicações.
Se a sugestão inicial estiver correta, retorne ela. Caso contrário, retorne o domínio correto."""
    
    try:
        intent_response = llm.invoke(intent_prompt)
        intent = intent_response.content.strip().lower()
        
        # Normalizar resposta da LLM para um dos domínios válidos
        intent_normalized = intent.replace(" ", "_").replace("-", "_")
        
        # Verificar se a resposta está nos domínios válidos
        for domain in AVAILABLE_DOMAINS:
            if domain in intent_normalized or intent_normalized in domain:
                return domain
        
        # Se não encontrou correspondência exata, usar a sugestão determinística
        return suggested_domain
        
    except Exception as e:
        # Em caso de erro na LLM, usar a sugestão determinística
        print(f"[WARNING Interpretation] Erro ao refinar domínio com LLM: {e}. Usando sugestão determinística: {suggested_domain}")
        return suggested_domain


def interpret(state: WorkflowState) -> WorkflowState:
    """
    Extrai domínio (intent) e entidades do texto de entrada usando Domain Routing.
    
    Processo em duas etapas:
    1. Detecção determinística: usa regras baseadas em palavras-chave para classificação rápida
    2. Refinamento com LLM: valida e refina a classificação sugerida
    
    Domínios disponíveis:
    - faturamento: questões relacionadas a valores, faturas, pagamentos
    - juridico: questões legais, contratos, processos
    - planos_e_cobertura: questões sobre planos e coberturas de procedimentos
    - cadastro: alterações e atualizações de dados cadastrais
    - atendimento: reclamações, solicitações, suporte
    - outros: casos que não se encaixam nos demais domínios
    
    Também extrai entidades estruturadas usando regex (procedimentos, valores, etc.).
    """
    input_text = state.get("input_text", "")
    
    # Extrair user_id e case_id do input_text se presente
    user_id = state.get("user_id")
    case_id = state.get("case_id")
    
    # Tentar extrair user_id do texto se não estiver no estado
    if not user_id:
        user_match = re.search(r"User:\s*(\w+)", input_text, re.IGNORECASE)
        if user_match:
            user_id = user_match.group(1)
    
    # Tentar extrair case_id do texto se não estiver no estado
    # Buscar padrões como "case: CASE-123", "case CASE-123", "CASE-123", etc
    if not case_id:
        case_match = re.search(r"case[:\s]+([A-Z0-9\-]+)", input_text, re.IGNORECASE)
        if not case_match:
            # Tentar padrão direto como "CASE-2026-001"
            case_match = re.search(r"(CASE-[A-Z0-9\-]+)", input_text, re.IGNORECASE)
        if case_match:
            case_id = case_match.group(1)
    
    # Extrair intenção usando Domain Routing
    # Passo 1: Análise determinística rápida
    intent = _detect_domain_deterministic(input_text)
    
    # Passo 2: Validação e refinamento com LLM
    intent = _refine_domain_with_llm(input_text, intent)
    
    # Extrair entidades usando regex e LLM
    entities = {}
    
    # Extrair procedimentos (códigos numéricos)
    procedimentos = re.findall(r"procedimento\s+(\d+)", input_text, re.IGNORECASE)
    if procedimentos:
        entities["procedimentos"] = procedimentos
    
    # Extrair valor total
    valor_match = re.search(r"valor\s+total\s+R\$\s*([\d.,]+)", input_text, re.IGNORECASE)
    if not valor_match:
        valor_match = re.search(r"R\$\s*([\d.,]+)", input_text)
    if valor_match:
        valor_str = valor_match.group(1).replace(".", "").replace(",", ".")
        try:
            entities["valor_total"] = float(valor_str)
        except ValueError:
            pass
    
    # Extrair medicamentos
    medicacoes = re.findall(r"medica[çc][õo]es?\s+([A-Z])", input_text, re.IGNORECASE)
    if not medicacoes:
        medicacoes = re.findall(r"medica[çc][õo]es?\s+([A-Za-z]+)", input_text, re.IGNORECASE)
    if medicacoes:
        entities["medicacoes"] = medicacoes
    
    # Extrair plano (se mencionado)
    plano_match = re.search(r"plano\s+(\w+)", input_text, re.IGNORECASE)
    if plano_match:
        entities["plano"] = plano_match.group(1).lower()
    
    # Extrair localidade (se mencionada)
    localidade_match = re.search(r"localidade[:\s]+(\w+)", input_text, re.IGNORECASE)
    if localidade_match:
        entities["localidade"] = localidade_match.group(1)
    
    # Se não encontrou valor_total mas encontrou apenas "valor", usar esse
    if "valor_total" not in entities and "valor" in entities:
        entities["valor_total"] = entities.pop("valor")
    
    result = {
        "intent": intent,
        "entities": entities,
    }
    
    # Preservar user_id e case_id se foram encontrados (do estado inicial ou extraídos do texto)
    # Isso garante que valores passados pela API sejam preservados no grafo
    if user_id:
        result["user_id"] = user_id
    if case_id:
        result["case_id"] = case_id
    
    return result
