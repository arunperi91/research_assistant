# backend/agents/summarizer_agent.py
from backend.services.openai_service import chat_completion
from backend.config import GPT_DEPLOYMENT

def summarize_text(text_blocks: list, topic: str) -> str:
    joined = "\n\n".join(text_blocks)[:8000] if text_blocks else "No content."
    system = {"role":"system","content":"You are a precise summarizer. 6-10 bullet points, concise, factual."}
    user = {"role":"user","content": f"Summarize key findings for '{topic}'. Use bullet points. Do not exceed 300 words.\n\n{joined}"}
    return chat_completion([system, user], model=GPT_DEPLOYMENT, temperature=0.2)
