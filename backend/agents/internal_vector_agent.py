from typing import List, Dict, Any
from backend.services.vector_store import ChromaVectorStore
from backend.config import TOP_K, MIN_SIMILARITY_THRESHOLD


class InternalVectorAgent:
    def __init__(self, store: ChromaVectorStore, threshold: float = MIN_SIMILARITY_THRESHOLD):
        self.store = store
        self.threshold = threshold

    def retrieve(self, query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        results = self.store.similarity_search(query, top_k=top_k, min_score=self.threshold)
        if not results:
            print(f"[INFO] No relevant internal documents found for: '{query}' (threshold: {self.threshold})")
        else:
            print(f"[INFO] Found {len(results)} relevant internal documents for: '{query}'")
        return results
