# backend/agents/internal_vector_agent.py

from typing import List, Dict, Any
from backend.services.vector_store import ChromaVectorStore
from backend.config import TOP_K

class InternalVectorAgent:
    def __init__(self, store: ChromaVectorStore):
        self.store = store

    def retrieve(self, query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        """
        Returns list of {'text': chunk_text, 'metadata': {...}} for citations.
        """
        results = self.store.similarity_search(query, top_k=top_k)
        return results
