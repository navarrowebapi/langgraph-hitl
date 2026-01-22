#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar conexão com Qdrant e listar regras indexadas.
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
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Setar variáveis de ambiente ANTES de importar
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

os.environ["QDRANT_HOST"] = QDRANT_HOST
os.environ["QDRANT_PORT"] = str(QDRANT_PORT)

print(f"[INFO] Verificando Qdrant em {QDRANT_HOST}:{QDRANT_PORT}")
print("=" * 60)

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

try:
    # Testar conexão
    client = qdrant_module._get_client()
    print("[OK] Conexao estabelecida!")
    
    # Listar coleções
    collections = client.get_collections()
    print(f"\n[INFO] Colecoes encontradas: {len(collections.collections)}")
    
    for col in collections.collections:
        print(f"\n  Colecao: {col.name}")
        info = client.get_collection(col.name)
        print(f"    - Pontos: {info.points_count}")
        print(f"    - Vetores: {info.config.params.vectors.size}")
    
    # Verificar coleção específica
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "empresa_m_regras")
    print(f"\n[INFO] Verificando colecao: {collection_name}")
    
    try:
        collection_info = client.get_collection(collection_name)
        print(f"[OK] Colecao '{collection_name}' existe!")
        print(f"   - Total de pontos: {collection_info.points_count}")
        
        # Buscar alguns pontos para verificar metadados
        if collection_info.points_count > 0:
            print(f"\n[INFO] Amostra de documentos (primeiros 3):")
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=3,
                with_payload=True,
                with_vectors=False
            )
            
            # scroll retorna (points, next_page_offset)
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result
            
            for i, point in enumerate(points[:3], 1):
                print(f"\n  Documento {i}:")
                print(f"    - ID: {point.id}")
                payload = point.payload
                print(f"    - Domain: {payload.get('domain', 'N/A')}")
                print(f"    - Rule ID: {payload.get('rule_id', 'N/A')}")
                print(f"    - Source: {payload.get('source', 'N/A')}")
                text = payload.get('page_content', '')
                if text:
                    print(f"    - Texto: {text[:60]}...")
        else:
            print(f"[WARNING] Colecao '{collection_name}' esta vazia!")
            print(f"   Execute: python scripts/ingest_regras_docker.py")
            
    except Exception as e:
        print(f"[ERROR] Colecao '{collection_name}' nao encontrada: {e}")
        print(f"   Execute: python scripts/ingest_regras_docker.py")
        
except Exception as e:
    print(f"[ERROR] Erro ao conectar: {e}")
    print(f"\n[INFO] Verifique:")
    print(f"   1. Qdrant esta rodando? docker ps --filter name=qdrant")
    print(f"   2. Porta correta? {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"   3. Variaveis de ambiente: QDRANT_HOST={QDRANT_HOST}, QDRANT_PORT={QDRANT_PORT}")
    sys.exit(1)

print("\n" + "=" * 60)
print("[OK] Verificacao concluida!")
