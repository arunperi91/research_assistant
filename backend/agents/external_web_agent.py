from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 6) -> list:
    results = []
    try:
        for item in DDGS().text(query, max_results=max_results):
            results.append({
                "title": item.get("title",""),
                "snippet": item.get("body",""),
                "url": item.get("href","")
            })
    except Exception:
        return []
    return results
