# ingest.py
import logging
import os
from services.vector_store import ChromaVectorStore
from config import DATA_DIR

# Configure logging with UTF-8 encoding for the file handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion_log.txt", encoding='utf-8'), # Explicitly set encoding
        logging.StreamHandler()
    ]
)

def main():
    """
    Main function to run the stateful ingestion process.
    This script finds new or modified documents in the data directory,
    processes them, and adds them to the ChromaDB vector store.
    """
    logging.info("--- Starting the stateful ingestion process... ---")
    
    if not os.path.exists(DATA_DIR):
        logging.error(f"Data directory not found at: {DATA_DIR}")
        logging.error("Please create the directory and add your documents.")
        return

    try:
        vector_store = ChromaVectorStore()
        summary = vector_store.ingest_directory_stateful(DATA_DIR)
        
        logging.info("--- Ingestion process finished. ---")
        logging.info("Summary:")
        logging.info(f"   - Documents Added: {summary.get('added', 0)}")
        logging.info(f"   - Documents Updated: {summary.get('updated', 0)}")
        logging.info(f"   - Documents Unchanged/Skipped: {summary.get('skipped', 0)}")
        
    except Exception as e:
        # Removed emoji to prevent encoding errors on Windows terminals
        logging.critical(f"An unexpected error occurred during ingestion: {e}", exc_info=True)

if __name__ == "__main__":
    main()