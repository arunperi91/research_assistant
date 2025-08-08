# backend/app.py (add imports)
from backend.services.vector_store import ChromaVectorStore
from backend.agents.internal_vector_agent import InternalVectorAgent
from backend.config import DATA_DIR

# Initialize Chroma on startup
print(f"[BOOT] Initializing Chroma store at {DATA_DIR}...")
VECTOR_STORE = ChromaVectorStore()
ingest_summary = VECTOR_STORE.ingest_directory(DATA_DIR)
print(f"[BOOT] Chroma ingest summary: {ingest_summary}")

# Replace previous INTERNAL_AGENT with vector agent
INTERNAL_AGENT = InternalVectorAgent(VECTOR_STORE)

# backend/app.py (only showing changed parts)
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.agents import planner, internal_data_agent, external_web_agent, summarizer_agent, citation_agent, image_agent, plagiarism_agent
from backend.services import session_service
from backend.config import FAQ_PDF_PATH
import os
import tempfile
import json
import textwrap
from fpdf import FPDF
import unicodedata
import re
import logging


# Setup logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler("backend_log.txt", encoding="utf-8"), logging.StreamHandler()]
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

def to_ascii_safe(text: str) -> str:
    # Replace common smart punctuation first
    text = (text.replace("'", "'")
                .replace("'", "'")
                .replace(""", '"')
                .replace(""", '"')
                .replace("—", "-")
                .replace("–", "-"))
    # Normalize and strip non-ASCII
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Optional: collapse repeated whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text

@app.post("/refresh_internal_index")
async def refresh_internal_index():
    logging.info("[REFRESH] Re-ingesting internal documents...")
    summary = VECTOR_STORE.ingest_directory(DATA_DIR)
    logging.info(f"[REFRESH] Summary: {summary}")
    return JSONResponse({"status": "ok", "summary": summary})

@app.post("/plan/")
async def generate_plan(request: Request):
    data = await request.json()
    logging.info(f"/plan/ request data: {data}")
    topic = data.get("topic", "").strip()
    if not topic:
        logging.warning("Missing 'topic' in /plan/ request")
        raise HTTPException(status_code=400, detail="Missing 'topic'")
    plan = planner.generate_research_plan(topic)
    logging.info(f"Generated plan: {plan}")
    sess = session_service.session_manager.get_session(request)
    logging.info(f"Session before update: {sess}")
    sess['plan'] = plan
    sess['topic'] = topic
    logging.info(f"Session after update: {sess}")
    return JSONResponse({"plan": plan})

@app.post("/execute/")
async def execute_plan(request: Request):
    logging.info("/execute/ endpoint called")
    data = await request.json()
    logging.info(f"/execute/ request data: {data}")
    plan = data.get('plan')

    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
            logging.info(f"Parsed plan JSON: {plan}")
        except Exception as e:
            logging.error(f"Error parsing plan JSON: {e}")
            raise HTTPException(status_code=400, detail="Plan must be valid JSON")

    if not isinstance(plan, dict) or 'steps' not in plan or 'topic' not in plan:
        logging.error(f"Invalid plan format: {plan}")
        raise HTTPException(status_code=422, detail="Plan JSON missing 'topic' or 'steps'")

    topic = plan['topic']
    steps = plan['steps']
    logging.info(f"Executing plan for topic: {topic}, steps: {steps}")
    sess = session_service.session_manager.get_session(request)
    logging.info(f"Session at execute: {sess}")

    report_sections, sources = [], []

    steps = steps[:5]
    logging.info(f"Steps limited to: {steps}")

    for step in steps:
        agent = step.get('agent')
        query = step.get('query', '')
        logging.info(f"Step: {step}")
        if not query:
            logging.warning("Skipping step with empty query")
            continue

        try:
            if agent == "internal":
                logging.info(f"Calling internal agent with query: {query}")
                relevant = INTERNAL_AGENT.retrieve(query)
                if relevant:
                    report_sections.append("\n\n".join([r["text"] for r in relevant]))
                    # Maintain rich metadata for citations
                    for r in relevant:
                        m = r["metadata"] or {}
                        title = m.get("file_name", "Internal Document")
                        page = m.get("page")
                        where = f"p.{page}" if page else ""
                        sources.append({
                            "title": f"{title} {where}".strip(),
                            "url": m.get("file_path", ""),  # local path as reference
                            "snippet": m.get("preview", "")
                        })

            elif agent == "external":
                logging.info(f"Calling external agent with query: {query}")
                results = external_web_agent.web_search(query)
                logging.info(f"External agent results: {results}")
                step_texts = [r.get('snippet', '') for r in results if r.get('snippet')]
                if step_texts:
                    report_sections.append("\n\n".join(step_texts))
                sources += results
        except Exception as e:
            logging.error(f"Error in step: {step}, error: {e}")
            continue

    logging.info(f"Report sections: {report_sections}")
    logging.info(f"Sources: {sources}")
    full_text = summarizer_agent.summarize_text(report_sections, topic)
    logging.info(f"Summarized text: {full_text}")
    cited_text = citation_agent.generate_citations(sources, full_text)
    logging.info(f"Cited text: {cited_text}")
    _ = plagiarism_agent.check_plagiarism(cited_text)
    logging.info("Plagiarism check complete")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Ensure topic and cited_text are ASCII-safe
    # This is important for PDF generation to avoid encoding issues
    topic_safe = to_ascii_safe(topic)
    cited_text_safe = to_ascii_safe(cited_text)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, txt=topic_safe, ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    for paragraph in cited_text_safe.split("\n\n"):
        for line in textwrap.wrap(paragraph, width=100):
            pdf.multi_cell(0, 6, line)
        pdf.ln(2)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        pdf_path = tmp_pdf.name
        logging.info(f"PDF created at: {pdf_path}")

    return FileResponse(pdf_path, media_type="application/pdf", filename="research_report.pdf")
