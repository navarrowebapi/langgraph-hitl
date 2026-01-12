from agent.rag.qdrant import add_documents
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os


def ingest_text(text: str, source: str = "manual"):
    """
    Ingestão direta de texto
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    metadata = [{"source": source} for _ in chunks]

    add_documents(chunks, metadata)


def ingest_folder(path: str):
    """
    Ingestão de todos os .txt de uma pasta
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
