import fitz
from typing import List

def extract_texts_from_pdf(pdf_path) -> List[str]:
    texts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            if text:
                texts.append(text)
    return texts

def chunk_text(text: str, max_tokens: int = 800):
    # Simple char-based chunking; you can replace with token-aware chunking
    chunk_size = max_tokens * 4  # approx chars
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
