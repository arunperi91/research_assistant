# backend/agents/citation_agent.py (adjust generate_citations to show file path if available)
def generate_citations(sources: list, summary: str) -> str:
    refs = []
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or "Source"
        url = s.get("url") or ""
        snippet = s.get("snippet") or ""
        line = f"[{i}] {title}"
        if url:
            line += f" — {url}"
        if snippet:
            # Keep preview concise
            sn = snippet.replace("\n", " ").strip()
            if len(sn) > 180:
                sn = sn[:177] + "..."
            line += f" — {sn}"
        refs.append(line)
    if not refs:
        return summary
    return f"{summary}\n\nReferences:\n" + "\n".join(refs)
