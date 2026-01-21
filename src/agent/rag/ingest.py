from agent.rag.qdrant import add_documents
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from typing import Optional


def ingest_text(text: str, source: str = "manual", base_metadata: Optional[dict] = None):
    """
    Ingestão direta de texto com metadados opcionais
    
    Args:
        text: Texto a ser indexado
        source: Nome da fonte (arquivo)
        base_metadata: Metadados base que serão aplicados a todos os chunks
                      Ex: {"section": "Aprovação", "rule_id": "REGRA-001", ...}
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    # Criar metadados para cada chunk
    metadata = []
    for chunk in chunks:
        chunk_meta = {"source": source}
        if base_metadata:
            chunk_meta.update(base_metadata)
        metadata.append(chunk_meta)

    add_documents(chunks, metadata)


def ingest_folder(path: str):
    """
    Ingestão de todos os .txt de uma pasta
    Mantido para compatibilidade - usa apenas source como metadado
    """
    texts = []
    metadata = []

    for filename in os.listdir(path):
        if filename.endswith(".txt"):
            full_path = os.path.join(path, filename)

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            texts.append(content)
            metadata.append({"source": filename})

    add_documents(texts, metadata)


def ingest_text_with_metadata(text: str, metadata: dict):
    """
    Ingestão de texto com metadados completos por chunk
    
    Args:
        text: Texto a ser indexado
        metadata: Dicionário com metadados completos:
                  {
                      "source": "arquivo.docx",
                      "section": "Seção",
                      "rule_id": "REGRA-001",
                      "page": "12",
                      "line_range": "89-90",
                      "tipo_regra": "faturamento",
                      "updated_at": "2024-01-15T10:00:00Z",
                      ...
                  }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    # Aplicar mesmos metadados a todos os chunks
    metadata_list = [metadata.copy() for _ in chunks]

    add_documents(chunks, metadata_list)
