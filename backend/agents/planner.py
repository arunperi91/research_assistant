import os
import json
from backend.services.openai_service import chat_completion
from backend.config import DATA_DIR, SUPPORTED_EXTS, GPT_DEPLOYMENT
from backend.agents.external_web_agent import web_search


def _list_internal_files() -> list:
    """List all available internal files in the data directory"""
    files = []
    try:
        for root, _, fns in os.walk(DATA_DIR):
            for fn in fns:
                ext = os.path.splitext(fn)[1].lower()
                if ext in SUPPORTED_EXTS:
                    file_path = os.path.join(root, fn)
                    files.append({
                        "title": fn, 
                        "type": ext.lstrip("."),
                        "path": file_path,
                        "preview": f"Internal document: {fn}"
                    })
    except Exception as e:
        print(f"[ERROR] Failed to list internal files: {e}")
    return files


def _get_internal_source_titles(chunks, topic: str, internal_agent) -> list:
    """Get comprehensive internal sources related to the topic"""
    titles = []
    seen_files = set()
    
    # Try multiple search queries to find relevant internal documents
    search_queries = [
        f"{topic} overview definition",
        f"{topic} principles guidelines", 
        f"{topic} implementation practices",
        f"{topic} framework standards",
        topic  # Basic topic search
    ]
    
    try:
        for query in search_queries:
            try:
                print(f"[DEBUG] Searching internal documents for: '{query}'")
                results = internal_agent.retrieve(query, top_k=5)
                
                if results:
                    print(f"[DEBUG] Found {len(results)} results for query: '{query}'")
                    for result in results:
                        meta = result.get("metadata", {}) or {}
                        fn = meta.get("file_name")
                        if fn and fn not in seen_files:
                            seen_files.add(fn)
                            ext = os.path.splitext(fn)[1].lower()
                            preview_text = meta.get("preview", "")[:150] + "..." if meta.get("preview") else ""
                            titles.append({
                                "title": fn, 
                                "type": ext.lstrip("."),
                                "preview": preview_text,
                                "relevance_score": result.get("score", 0)
                            })
                else:
                    print(f"[DEBUG] No results found for query: '{query}'")
                    
            except Exception as e:
                print(f"[WARNING] Internal search failed for query '{query}': {e}")
                continue
                
    except Exception as e:
        print(f"[ERROR] Internal source discovery failed: {e}")
    
    # If no relevant results found, return empty list (don't fall back to all files)
    if not titles:
        print(f"[INFO] No relevant internal documents found for topic: '{topic}'")
        return []  # Return empty list instead of fallback files
    
    # Sort by relevance score if available, otherwise keep original order
    titles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    print(f"[INFO] Found {len(titles)} relevant internal documents for topic: '{topic}'")
    return titles[:10]  # Return top 10 most relevant


def _preview_external_sources(topic: str) -> list:
    """Preview external sources with better error handling and multiple search attempts"""
    external_sources = []
    
    # Try multiple search variations
    search_queries = [
        f"{topic} overview guide",
        f"{topic} best practices",
        f"{topic} latest trends 2024",
        f"what is {topic}",
        topic
    ]
    
    for query in search_queries:
        try:
            print(f"[DEBUG] Searching external sources for: '{query}'")
            results = web_search(query, max_results=3)
            
            for r in results:
                url = r.get("url")
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                
                if not url:
                    continue
                
                # Extract domain safely
                try:
                    domain = url.split("//")[-1].split("/")[0]
                    if domain.startswith("www."):
                        domain = domain[4:]
                except Exception:
                    domain = url[:50] + "..." if len(url) > 50 else url
                
                # Check if we already have this domain
                if any(src.get("name") == domain for src in external_sources):
                    continue
                
                external_sources.append({
                    "name": domain,
                    "type": "web",
                    "url": url,
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "preview": snippet[:200] + "..." if len(snippet) > 200 else snippet
                })
                
                # Stop when we have enough sources
                if len(external_sources) >= 8:
                    break
            
            if len(external_sources) >= 8:
                break
                
        except Exception as e:
            print(f"[WARNING] External search failed for query '{query}': {e}")
            continue
    
    print(f"[INFO] Found {len(external_sources)} external sources")
    return external_sources


def generate_research_plan(topic: str, internal_agent) -> dict:
    """Generate a comprehensive research plan with proper source discovery"""
    print(f"[INFO] Generating research plan for topic: '{topic}'")
    
    # Discover internal sources with comprehensive search
    print("[INFO] Discovering internal sources...")
    internal_sources = _get_internal_source_titles([], topic, internal_agent)
    print(f"[INFO] Found {len(internal_sources)} relevant internal sources")
    
    # Preview external sources with multiple search attempts
    print("[INFO] Previewing external sources...")
    external_sources = _preview_external_sources(topic)
    print(f"[INFO] Found {len(external_sources)} external sources")
    
    # Generate research plan and steps via LLM
    print("[INFO] Generating research steps...")
    system = {
        "role": "system",
        "content": (
            "You are a senior research planner. Create a comprehensive research plan with 4-6 specific research steps. "
            "Each step should focus on a different aspect of the topic. "
            "First provide a brief plan overview, then output JSON with 'steps' containing research questions."
        )
    }
    
    user = {
        "role": "user",
        "content": f"""Create a research plan for: "{topic}"

Generate 4-6 research steps that cover:
- Definition and key concepts
- Current trends and developments  
- Implementation practices
- Benefits and challenges
- Future outlook
- Real-world applications

Format:
PLAN_TEXT: Brief overview of the research approach (1-2 sentences)

JSON:
{{"steps": [{{"query": "specific research question 1"}}, {{"query": "specific research question 2"}}, ...]}}
"""
    }

    try:
        raw = chat_completion([system, user], model=GPT_DEPLOYMENT, temperature=0.2)
        print(f"[DEBUG] LLM response: {raw[:200]}...")
        
        plan_text = ""
        steps = []
        
        if "JSON:" in raw:
            parts = raw.split("JSON:")
            plan_text = parts[0].replace("PLAN_TEXT:", "").strip()
            json_part = parts[1].strip()
        else:
            # Try to extract JSON from the response
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                plan_text = raw[:json_start].replace("PLAN_TEXT:", "").strip()
                json_part = raw[json_start:json_end]
            else:
                json_part = raw
                plan_text = f"Comprehensive research analysis of {topic}"
        
        try:
            parsed = json.loads(json_part)
            steps = parsed.get("steps", [])
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing failed: {e}")
            raise
            
    except Exception as e:
        print(f"[ERROR] Plan generation failed: {e}")
        # Fallback to default steps
        steps = [
            {"query": f"What is {topic} and what are its key components and principles?"},
            {"query": f"What are the latest developments and trends in {topic} for 2024?"},
            {"query": f"What are the main benefits and advantages of implementing {topic}?"},
            {"query": f"What are the key challenges and limitations of {topic}?"},
            {"query": f"What are best practices for implementing {topic} in organizations?"},
            {"query": f"What is the future outlook and emerging trends for {topic}?"},
        ]
        plan_text = f"Comprehensive research covering definition, trends, benefits, challenges, implementation, and future outlook of {topic}."

    # Ensure we have at least some steps
    if not steps:
        steps = [
            {"query": f"Define {topic} and explain its core concepts"},
            {"query": f"Analyze current trends and developments in {topic}"},
            {"query": f"Evaluate benefits and challenges of {topic}"},
            {"query": f"Assess future prospects for {topic}"},
        ]
        plan_text = f"Systematic analysis of {topic} covering key aspects and implications."

    final_plan = {
        "topic": topic,
        "plan_text": plan_text,
        "steps": steps,
        "internal_sources": internal_sources,
        "external_sources": external_sources,
    }
    
    print(f"[INFO] Plan generated with {len(steps)} steps, {len(internal_sources)} internal sources, {len(external_sources)} external sources")
    return final_plan
