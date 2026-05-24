import fitz  # PyMuPDF
import json
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNKS_FILE = "./resume_chunks.json"

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

def build_resume_index(pdf_path: str) -> list:
    text = extract_text(pdf_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60
    )
    chunks = splitter.split_text(text)

    # Save chunks to a simple JSON file — no downloads needed
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f)

    return chunks

def get_resume_context(chunks: list, query: str, k: int = 3) -> str:
    """
    Simple keyword search — finds chunks that contain
    words from the query. No embeddings, no internet needed.
    """
    query_words = set(query.lower().split())

    # Score each chunk by how many query words it contains
    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for word in query_words if word in chunk_lower)
        scored.append((score, chunk))

    # Sort by score descending, take top k
    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in scored[:k]]

    return "\n---\n".join(top_chunks)

def load_resume_chunks() -> list:
    """Load previously saved chunks."""
    if os.path.exists(CHUNKS_FILE):
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []