# backend/agents/internal_data_agent.py
from backend.services.pdf_service import extract_texts_from_pdf, chunk_text
from backend.services.openai_service import get_embedding
from typing import List, Tuple
import numpy as np

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

class InternalDataAgent:
    def __init__(self, pdf_path: str):
        pages = extract_texts_from_pdf(pdf_path)
        text = "\n\n".join(pages) if pages else "No internal FAQ content found."
        # Cap to a few chunks to avoid excessive embedding calls
        chunks = []
        for p in pages:
            chunks.extend(chunk_text(p, max_tokens=600))
            if len(chunks) >= 12:  # cap to 12 chunks
                break
        if not chunks:
            chunks = chunk_text(text, max_tokens=600)[:8]
        self.text_chunks: List[str] = chunks
        self.embeddings = [np.array(get_embedding(t), dtype=np.float32) for t in self.text_chunks]

    def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        q_emb = np.array(get_embedding(query), dtype=np.float32)
        sims = [(_cosine_sim(e, q_emb), i) for i, e in enumerate(self.embeddings)]
        sims.sort(reverse=True, key=lambda x: x[0])
        top = sims[:max(1, top_k)]
        return [(self.text_chunks[i], s) for s, i in top]
