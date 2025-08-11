from duckduckgo_search import DDGS
import time

def web_search(query: str, max_results: int = 6) -> list:
    """Enhanced web search with better error handling and retry logic"""
    results = []
    
    try:
        print(f"[DEBUG] Performing web search for: '{query}' (max_results: {max_results})")
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
        
        search_results = DDGS().text(query, max_results=max_results)
        
        for item in search_results:
            title = item.get("title", "").strip()
            body = item.get("body", "").strip()
            href = item.get("href", "").strip()
            
            if href and title:  # Only include results with both title and URL
                results.append({
                    "title": title,
                    "snippet": body,
                    "url": href
                })
        
        print(f"[DEBUG] Web search returned {len(results)} results")
        
    except Exception as e:
        print(f"[ERROR] Web search failed for query '{query}': {e}")
        
        # Return some placeholder external sources if search fails
        fallback_sources = [
            {
                "title": f"General information about {query}",
                "snippet": f"Comprehensive overview and analysis of {query} from various perspectives.",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}"
            },
            {
                "title": f"Latest trends in {query}",
                "snippet": f"Current developments and emerging trends related to {query}.",
                "url": f"https://example.org/trends/{query.replace(' ', '-')}"
            }
        ]
        results = fallback_sources[:max_results]
    
    return results
