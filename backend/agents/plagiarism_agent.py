# backend/agents/plagiarism_agent.py
import re
import time
import random
from duckduckgo_search import DDGS

# Check what percentage of sentences need to be found online to trigger a flag.
# 15% is a reasonable starting point.
SENTENCE_MATCH_THRESHOLD = 0.15 
# How many sentences to check. Checking all can be slow, so we sample.
SAMPLE_SIZE = 20 

def check_plagiarism(text: str) -> dict:
    """
    Performs a basic plagiarism check by searching for exact sentences online.
    """
    # Use regex to split the text into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10] # Filter out short/empty sentences

    if not sentences:
        return {"plagiarism_score": 0, "is_plagiarized": False, "details": "No text to check."}

    # To avoid being slow, we check a random sample of sentences
    num_to_check = min(len(sentences), SAMPLE_SIZE)
    sentences_to_check = random.sample(sentences, num_to_check)
    
    matches_found = 0
    matched_sentences = []

    ddgs = DDGS()

    for sentence in sentences_to_check:
        # The key is to search for the exact sentence in quotes
        query = f'"{sentence}"'
        try:
            # We only need to know if there's at least ONE result.
            search_results = list(ddgs.text(query, max_results=1))
            if search_results:
                matches_found += 1
                matched_sentences.append({
                    "sentence": sentence,
                    "source": search_results[0]['href']
                })
            time.sleep(0.5) # Be polite to the API to avoid rate-limiting
        except Exception as e:
            print(f"Error during web search for plagiarism check: {e}")
            continue

    plagiarism_score = (matches_found / num_to_check) if num_to_check > 0 else 0
    is_plagiarized = plagiarism_score >= SENTENCE_MATCH_THRESHOLD

    return {
        "plagiarism_score": round(plagiarism_score * 100, 2), # As a percentage
        "is_plagiarized": is_plagiarized,
        "matches": matched_sentences
    }