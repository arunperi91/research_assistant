# backend/services/vector_store.py
import os
import hashlib
import logging
import json
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import (
    CHROMA_DIR, CHROMA_COLLECTION, SUPPORTED_EXTS,
    CHUNK_SIZE, CHUNK_OVERLAP, MIN_SIMILARITY_THRESHOLD
)
from .openai_service import get_embedding

logger = logging.getLogger(__name__)

# --- Helper functions (read_text_from_pdf, etc.) are unchanged ---
def read_text_from_pdf(path: str) -> List[Dict[str, Any]]:
    blocks = []
    try:
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip(): blocks.append({"page": i + 1, "text": text})
    except Exception as e:
        logger.error(f"Error reading PDF {path}: {e}")
    return blocks

def read_text_from_file(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if text.strip(): return [{"page": 1, "text": text}]
    except Exception as e:
        logger.error(f"Error reading text file {path}: {e}")
    return []

def load_file_blocks(path: str) -> List[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf": return read_text_from_pdf(path)
    if ext in [".txt", ".md"]: return read_text_from_file(path)
    return []

def chunk_blocks(blocks: List[Dict[str, Any]], file_name: str, file_path: str) -> List[Dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_chunks = []
    for block in blocks:
        page_num, text = block.get("page", 1), block.get("text", "")
        parts = splitter.split_text(text)
        for i, part in enumerate(parts):
            if not part.strip(): continue
            chunk_id_str = f"{file_path}_{page_num}_{i}"
            chunk_id = hashlib.sha256(chunk_id_str.encode()).hexdigest()
            all_chunks.append({
                "text": part,
                "metadata": {"id": chunk_id, "file_name": file_name, "file_path": file_path, "page": page_num, "chunk_index": i, "preview": part[:200].replace("\n", " ").strip() + "..."}
            })
    return all_chunks

def file_fingerprint(path: str) -> str:
    stat = os.stat(path)
    payload = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(payload.encode()).hexdigest()
# --- End of unchanged helper functions ---


class ChromaVectorStore:
    def __init__(self, persist_dir: Optional[str] = None, collection_name: Optional[str] = None):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.collection_name = collection_name or CHROMA_COLLECTION
        self.index_file_path = os.path.join(self.persist_dir, "chroma_index.json")
        logger.info(f"Connecting to persistent ChromaVectorStore at: {self.persist_dir}")
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.Client(Settings(persist_directory=self.persist_dir, is_persistent=True))
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            logger.warning(f"Collection '{self.collection_name}' not found. Creating new one.")
            return self.client.create_collection(name=self.collection_name, metadata={"hnsw:space": "cosine"})

    def _load_ingestion_index(self) -> Dict[str, str]:
        if not os.path.exists(self.index_file_path): return {}
        try:
            with open(self.index_file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except (json.JSONDecodeError, IOError): return {}

    def _save_ingestion_index(self, index: Dict[str, str]):
        with open(self.index_file_path, 'w', encoding='utf-8') as f: json.dump(index, f, indent=2)

    def _delete_chunks_by_filepath(self, file_path: str):
        logger.info(f"Deleting old chunks for updated file: {file_path}")
        self.collection.delete(where={"file_path": file_path})

    def ingest_directory_stateful(self, dir_path: str) -> Dict[str, int]:
        index = self._load_ingestion_index()
        summary = {"added": 0, "updated": 0, "skipped": 0}

        for root, _, files in os.walk(dir_path):
            for file_name in files:
                if os.path.splitext(file_name)[1].lower() not in SUPPORTED_EXTS:
                    continue
                
                # *** FIX IS HERE ***
                # Define file_path first...
                file_path = os.path.join(root, file_name)
                # ...then use it to get the fingerprint.
                current_fp = file_fingerprint(file_path)
                
                if file_path not in index:
                    status = "added"
                elif index[file_path] != current_fp:
                    status = "updated"
                    self._delete_chunks_by_filepath(file_path)
                else:
                    summary["skipped"] += 1
                    continue
                
                logger.info(f"Processing ({status}) file: {file_name}")
                try:
                    blocks = load_file_blocks(file_path)
                    if not blocks: continue
                    chunks = chunk_blocks(blocks, file_name, file_path)
                    if not chunks: continue

                    ids = [c['metadata']['id'] for c in chunks]
                    texts = [c['text'] for c in chunks]
                    metadatas = [c['metadata'] for c in chunks]
                    embeddings = [get_embedding(t) for t in texts]
                    self.collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
                    
                    index[file_path] = current_fp
                    summary[status] = summary.get(status, 0) + 1
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
        
        self._save_ingestion_index(index)
        return summary
        
    def similarity_search(self, query: str, top_k: int = 3, min_score: float = None) -> List[Dict[str, Any]]:
        min_score = min_score if min_score is not None else MIN_SIMILARITY_THRESHOLD
        if self.collection.count() == 0: return []
        try:
            query_embedding = get_embedding(query)
            results = self.collection.query(query_embeddings=[query_embedding], n_results=max(top_k * 5, 20), include=["documents", "metadatas", "distances"])
        except Exception as e:
            logger.error(f"ChromaDB query or embedding failed: {e}", exc_info=True)
            return []
        docs, metadatas, distances = results.get('documents', [[]])[0], results.get('metadatas', [[]])[0], results.get('distances', [[]])[0]
        if not docs: return []
        output = []
        for doc, meta, dist in zip(docs, metadatas, distances):
            similarity = 1 - dist
            if similarity >= min_score: output.append({"text": doc, "metadata": meta, "score": similarity})
        output.sort(key=lambda x: x["score"], reverse=True)
        return output[:top_k]