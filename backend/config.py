import os
from dotenv import load_dotenv

load_dotenv()  

import os

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
API_VERSION = os.getenv("API_VERSION", "2024-02-15-preview")  # keep aligned with your resource availability[18][17]

# Deployed model "deployment names" in Azure (not model families)
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
GPT_DEPLOYMENT = os.getenv("GPT_DEPLOYMENT", "gpt-4.1")  # or your actual deployment name

# Paths
BASE_DIR = os.path.dirname(__file__)
FAQ_PDF_PATH = os.path.join(BASE_DIR, "data", "Responsible-AI-Transparency-Report-2024.pdf")

# Sessions
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this_in_prod")




# backend/config.py (append or ensure these exist)

# Vector store
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(BASE_DIR, "chroma_store"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "internal_docs")

# Data ingestion
DATA_DIR = os.path.join(BASE_DIR, "data")
SUPPORTED_EXTS = {".pdf", ".txt", ".md"}  # add .docx later if needed
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))       # characters, approx token-aware
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # characters
TOP_K = int(os.getenv("TOP_K", "3"))                    # retrieval top-k
