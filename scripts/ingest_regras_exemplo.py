"""
Script de exemplo para indexar regras no Qdrant com metadados completos.

Uso:
    python scripts/ingest_regras_exemplo.py
    
Nota: Requer OPENAI_API_KEY configurada no ambiente ou arquivo .env
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Adicionar src ao path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Carregar variáveis de ambiente do .env se existir
from dotenv import load_dotenv
load_dotenv()

# Verificar se OPENAI_API_KEY está configurada
if not os.getenv("OPENAI_API_KEY"):
    print("AVISO: OPENAI_API_KEY nao encontrada!")
    print("   Configure a variavel de ambiente ou crie um arquivo .env")
    print("   Exemplo: export OPENAI_API_KEY='sua-chave-aqui'")
    print("\n   Continuando mesmo assim... (pode falhar na criacao de embeddings)\n")

# Importar módulos necessários diretamente do arquivo para evitar __init__.py
import importlib.util

# Carregar qdrant.py diretamente
qdrant_spec = importlib.util.spec_from_file_location(
    "qdrant", 
    src_path / "agent" / "rag" / "qdrant.py"
)
qdrant_module = importlib.util.module_from_spec(qdrant_spec)
qdrant_spec.loader.exec_module(qdrant_module)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Usar funções do módulo qdrant carregado
add_documents = qdrant_module.add_documents


def ingest_text_with_metadata(text: str, metadata: dict):
    """
    Ingestão de texto com metadados completos por chunk
    (versão standalone para evitar imports desnecessários)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    # Aplicar mesmos metadados a todos os chunks
    metadata_list = [metadata.copy() for _ in chunks]

    add_documents(chunks, metadata_list)


def main():
    """Indexa regras de exemplo com metadados completos"""
    
    print("Iniciando ingestao de regras no Qdrant...")
    print("=" * 60)
    
    # ===========================================
    # REGRA 1: Aprovação de Faturamento
    # ===========================================
    print("\nIndexando REGRA FAT-001...")
    texto_regra_1 = """
    Procedimentos com valor acima de R$ 500,00 requerem aprovação humana antes do faturamento. 
    Esta regra se aplica a todos os planos, exceto planos premium que possuem limite de R$ 1.000,00.
    """
    
    metadata_1 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Aprovação de Faturamento",
        "rule_id": "REGRA-FAT-001",
        "page": "1",
        "line_range": "5-6",
        "tipo_regra": "faturamento",
        "domain": "faturamento",  # Domain Routing: faturamento
        "updated_at": "2024-01-15T10:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Faturamento"
    }
    
    ingest_text_with_metadata(texto_regra_1.strip(), metadata_1)
    print("OK - REGRA FAT-001 indexada")
    
    # ===========================================
    # REGRA 2: Auditoria para Planos Premium
    # ===========================================
    print("\nIndexando REGRA FAT-002...")
    texto_regra_2 = """
    Planos premium com procedimentos acima de R$ 1.000,00 devem passar por auditoria prévia. 
    A auditoria deve ser concluída em até 48 horas após a solicitação.
    """
    
    metadata_2 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Aprovação de Faturamento",
        "rule_id": "REGRA-FAT-002",
        "page": "1",
        "line_range": "7-8",
        "tipo_regra": "auditoria",
        "domain": "faturamento",  # Domain Routing: faturamento (auditoria de faturamento)
        "updated_at": "2024-01-15T10:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Faturamento"
    }
    
    ingest_text_with_metadata(texto_regra_2.strip(), metadata_2)
    print("OK - REGRA FAT-002 indexada")
    
    # ===========================================
    # REGRA 3: Urgência e Emergência
    # ===========================================
    print("\nIndexando REGRA FAT-003...")
    texto_regra_3 = """
    Procedimentos de urgência e emergência não requerem aprovação prévia, independente do valor, 
    mas devem ser auditados posteriormente.
    """
    
    metadata_3 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Aprovação de Faturamento",
        "rule_id": "REGRA-FAT-003",
        "page": "1",
        "line_range": "9-10",
        "tipo_regra": "faturamento",
        "domain": "faturamento",  # Domain Routing: faturamento
        "updated_at": "2024-01-15T10:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Faturamento"
    }
    
    ingest_text_with_metadata(texto_regra_3.strip(), metadata_3)
    print("OK - REGRA FAT-003 indexada")
    
    # ===========================================
    # REGRA 4: Cobertura de Procedimentos
    # ===========================================
    print("\nIndexando REGRA COB-001...")
    texto_regra_4 = """
    Procedimento código 3344 (Consulta Cardiológica) é coberto para todos os planos. 
    Não requer autorização prévia.
    """
    
    metadata_4 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Cobertura de Procedimentos",
        "rule_id": "REGRA-COB-001",
        "page": "2",
        "line_range": "15-16",
        "tipo_regra": "cobertura",
        "domain": "planos_e_cobertura",  # Domain Routing: planos_e_cobertura
        "updated_at": "2024-01-10T14:30:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Cobertura"
    }
    
    ingest_text_with_metadata(texto_regra_4.strip(), metadata_4)
    print("OK - REGRA COB-001 indexada")
    
    # ===========================================
    # REGRA 5: Exame de Sangue
    # ===========================================
    print("\nIndexando REGRA COB-002...")
    texto_regra_5 = """
    Procedimento código 5566 (Exame de Sangue Completo) requer autorização prévia para planos básicos, 
    mas é automático para planos premium e empresariais.
    """
    
    metadata_5 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Cobertura de Procedimentos",
        "rule_id": "REGRA-COB-002",
        "page": "2",
        "line_range": "17-18",
        "tipo_regra": "cobertura",
        "domain": "planos_e_cobertura",  # Domain Routing: planos_e_cobertura
        "updated_at": "2024-01-10T14:30:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Cobertura"
    }
    
    ingest_text_with_metadata(texto_regra_5.strip(), metadata_5)
    print("OK - REGRA COB-002 indexada")
    
    # ===========================================
    # REGRA 6: Auditoria para Valores Altos
    # ===========================================
    print("\nIndexando REGRA AUD-001...")
    texto_regra_6 = """
    Casos com valor total acima de R$ 2.000,00 devem passar por auditoria completa antes do faturamento.
    """
    
    metadata_6 = {
        "source": "Politica_Faturamento_2024.txt",
        "section": "Regras de Auditoria",
        "rule_id": "REGRA-AUD-001",
        "page": "3",
        "line_range": "23-24",
        "tipo_regra": "auditoria",
        "domain": "faturamento",  # Domain Routing: faturamento (auditoria de faturamento)
        "updated_at": "2024-01-15T10:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Auditoria"
    }
    
    ingest_text_with_metadata(texto_regra_6.strip(), metadata_6)
    print("OK - REGRA AUD-001 indexada")
    
    # ===========================================
    # REGRA 7: Contrato - Limites de Cobertura
    # ===========================================
    print("\nIndexando CLAUSULA 1.1...")
    texto_regra_7 = """
    O plano básico cobre até R$ 5.000,00 por mês em procedimentos. 
    Valores acima deste limite requerem aprovação especial do comitê médico.
    """
    
    metadata_7 = {
        "source": "Contrato_Operadora_XYZ.txt",
        "section": "Limites de Cobertura",
        "rule_id": "CLÁUSULA-1.1",
        "page": "1",
        "line_range": "5-6",
        "tipo_regra": "cobertura",
        "domain": "planos_e_cobertura",  # Domain Routing: planos_e_cobertura
        "updated_at": "2024-01-01T00:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Cobertura"
    }
    
    ingest_text_with_metadata(texto_regra_7.strip(), metadata_7)
    print("OK - CLAUSULA 1.1 indexada")
    
    # ===========================================
    # REGRA 8: Contrato - Autorização Prévia
    # ===========================================
    print("\nIndexando CLAUSULA 2.1...")
    texto_regra_8 = """
    Procedimentos com valor acima de R$ 300,00 requerem autorização prévia, 
    exceto urgências e emergências.
    """
    
    metadata_8 = {
        "source": "Contrato_Operadora_XYZ.txt",
        "section": "Autorização Prévia",
        "rule_id": "CLÁUSULA-2.1",
        "page": "2",
        "line_range": "10-11",
        "tipo_regra": "faturamento",
        "domain": "faturamento",  # Domain Routing: faturamento
        "updated_at": "2024-01-01T00:00:00Z",
        "valid_from": "2024-01-01T00:00:00Z",
        "departamento": "Faturamento"
    }
    
    ingest_text_with_metadata(texto_regra_8.strip(), metadata_8)
    print("OK - CLAUSULA 2.1 indexada")
    
    print("\n" + "=" * 60)
    print("OK - Ingestao concluida! Total de 8 regras indexadas.")
    print("\nProximos passos:")
    print("   1. Verifique se o Qdrant esta rodando: docker-compose ps qdrant")
    print("   2. Teste a busca via API: POST /agent/invoke")
    print("   3. Verifique retrieved_rules no estado do grafo")


if __name__ == "__main__":
    main()
