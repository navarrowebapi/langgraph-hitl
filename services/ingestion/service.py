"""
Serviço de Ingestão Reutilizável

Lógica central de ingestão que pode ser usada por qualquer projeto.
Configuração via variáveis de ambiente.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Adicionar src ao path para importar módulos do projeto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from agent.rag.ingest import ingest_text_with_metadata
from services.ingestion.parser import RuleParser


class IngestionService:
    """
    Serviço de ingestão reutilizável
    
    Configuração via variáveis de ambiente:
    - INGESTION_DOCS_PATH: Caminho para pasta com documentos (padrão: docs_regras/)
    - QDRANT_HOST: Host do Qdrant (padrão: localhost)
    - QDRANT_PORT: Porta do Qdrant (padrão: 6333)
    - QDRANT_COLLECTION_NAME: Nome da coleção (padrão: empresa_m_regras)
    """
    
    def __init__(self, docs_path: Optional[str] = None):
        """
        Inicializa o serviço de ingestão
        
        Args:
            docs_path: Caminho para pasta com documentos. Se None, usa INGESTION_DOCS_PATH
        """
        self.docs_path = docs_path or os.getenv(
            "INGESTION_DOCS_PATH", 
            str(project_root / "docs_regras")
        )
        
        # Garantir que o caminho existe
        if not os.path.exists(self.docs_path):
            raise ValueError(f"Pasta de documentos não encontrada: {self.docs_path}")
        
        print(f"📁 Serviço de Ingestão inicializado")
        print(f"   Pasta de documentos: {self.docs_path}")
    
    def ingest_all(self) -> Dict[str, any]:
        """
        Ingesta todos os arquivos da pasta configurada
        
        Returns:
            Dicionário com estatísticas da ingestão
        """
        print(f"\n🚀 Iniciando ingestão de documentos...")
        print(f"   Pasta: {self.docs_path}")
        print("=" * 60)
        
        # Parsear todos os arquivos
        all_rules = RuleParser.parse_folder(self.docs_path)
        
        if not all_rules:
            print("⚠️  Nenhuma regra encontrada nos arquivos!")
            return {
                "success": False,
                "rules_indexed": 0,
                "files_processed": 0,
                "error": "Nenhuma regra encontrada"
            }
        
        # Indexar cada regra
        rules_indexed = 0
        files_processed = set()
        
        for rule_data in all_rules:
            try:
                ingest_text_with_metadata(
                    text=rule_data["text"],
                    metadata=rule_data["metadata"]
                )
                rules_indexed += 1
                files_processed.add(rule_data["metadata"]["source"])
                
                if rules_indexed % 10 == 0:
                    print(f"   ✅ {rules_indexed} regras indexadas...")
                    
            except Exception as e:
                print(f"   ❌ Erro ao indexar regra {rule_data['metadata'].get('rule_id', 'desconhecida')}: {e}")
        
        print("=" * 60)
        print(f"✅ Ingestão concluída!")
        print(f"   Regras indexadas: {rules_indexed}")
        print(f"   Arquivos processados: {len(files_processed)}")
        
        return {
            "success": True,
            "rules_indexed": rules_indexed,
            "files_processed": len(files_processed),
            "files": list(files_processed),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def ingest_file(self, filename: str) -> Dict[str, any]:
        """
        Ingesta um arquivo específico
        
        Args:
            filename: Nome do arquivo (deve estar na pasta configurada)
            
        Returns:
            Dicionário com estatísticas da ingestão
        """
        file_path = os.path.join(self.docs_path, filename)
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"Arquivo não encontrado: {file_path}"
            }
        
        print(f"\n🚀 Iniciando ingestão do arquivo: {filename}")
        
        # Parsear arquivo
        rules = RuleParser.parse_file(file_path)
        
        if not rules:
            return {
                "success": False,
                "error": "Nenhuma regra encontrada no arquivo"
            }
        
        # Indexar regras
        rules_indexed = 0
        for rule_data in rules:
            try:
                ingest_text_with_metadata(
                    text=rule_data["text"],
                    metadata=rule_data["metadata"]
                )
                rules_indexed += 1
            except Exception as e:
                print(f"   ❌ Erro ao indexar regra: {e}")
        
        print(f"✅ Arquivo processado: {rules_indexed} regras indexadas")
        
        return {
            "success": True,
            "rules_indexed": rules_indexed,
            "file": filename,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_status(self) -> Dict[str, any]:
        """
        Retorna status do serviço
        
        Returns:
            Dicionário com informações do serviço
        """
        files = list(Path(self.docs_path).glob("*.txt"))
        
        return {
            "docs_path": self.docs_path,
            "files_count": len(files),
            "files": [f.name for f in files]
        }
