# -*- coding: utf-8 -*-
"""Teste simples de busca no Qdrant"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Setar variáveis ANTES de importar
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"

from dotenv import load_dotenv
load_dotenv()

# Importar módulo qdrant
import importlib.util
qdrant_spec = importlib.util.spec_from_file_location(
    "qdrant", 
    src_path / "agent" / "rag" / "qdrant.py"
)
qdrant_module = importlib.util.module_from_spec(qdrant_spec)
qdrant_spec.loader.exec_module(qdrant_module)

# Resetar conexões
if hasattr(qdrant_module, '_reset_connections'):
    qdrant_module._reset_connections()

print("Testando busca no Qdrant...")
print("=" * 60)

# Testar busca sem filtro
print("\n1. Busca sem filtro (query: 'faturamento'):")
results = qdrant_module.search_docs_with_metadata("faturamento", k=3, domain=None)
print(f"   Encontrados: {len(results)} resultados")

for i, doc in enumerate(results, 1):
    print(f"\n   Resultado {i}:")
    print(f"   - Domain: {doc.metadata.get('domain', 'N/A')}")
    print(f"   - Rule ID: {doc.metadata.get('rule_id', 'N/A')}")
    print(f"   - Source: {doc.metadata.get('source', 'N/A')}")
    print(f"   - Texto: {doc.page_content[:80]}...")

# Testar busca com filtro
print("\n2. Busca COM filtro domain='faturamento':")
results_filtered = qdrant_module.search_docs_with_metadata("faturamento", k=3, domain="faturamento")
print(f"   Encontrados: {len(results_filtered)} resultados")

for i, doc in enumerate(results_filtered, 1):
    print(f"\n   Resultado {i}:")
    print(f"   - Domain: {doc.metadata.get('domain', 'N/A')}")
    print(f"   - Rule ID: {doc.metadata.get('rule_id', 'N/A')}")
    print(f"   - Source: {doc.metadata.get('source', 'N/A')}")

print("\n" + "=" * 60)
print("Teste concluido!")
