Step 1 : activate virtual env
Step 2 : add data to data folder and run "python ingest.py" to create embeddings
Step 4 : uvicorn backend.app:app --reload --port 8082
Step 4 : streamlit run frontend/main.py