# backend/agents/planner.py
import json
from backend.services.openai_service import chat_completion
from backend.config import GPT_DEPLOYMENT

def generate_research_plan(topic: str) -> dict:
    """
    Returns:
    {
      "topic": str,
      "plan_text": "(1) ... (2) ... (3) ...",
      "steps": [ {agent, query, needs}, ... ],
      "internal_sources": [ {title, type}, ... ],
      "external_sources": [ {name, type, note}, ... ]
    }
    """
    system = {
        "role": "system",
        "content": (
            "You are a senior research planner. "
            "Produce a concise numbered research plan as a single paragraph, with steps numbered (1)...(N). "
            "Then also produce a compact machine-readable JSON section: "
            "steps (array of 3-6 steps with {agent: 'internal'|'external', query, needs: []}), "
            "internal_sources (array of {title, type}), "
            "external_sources (array of {name, type, note}). "
            "Do not include any prose outside the specified sections."
        )
    }

    user = {
        "role": "user",
        "content": f"""
Topic: "{topic}"

Output STRICTLY in this template:

PLAN_TEXT:
(1) <first step>. (2) <second step>. (3) <third step>. (4) <...>. (5) <...>. (6) <...>. (7) <...>. (8) <...>

JSON:
{{
  "steps": [
    {{"agent": "internal", "query": "<what to retrieve from internal FAQ>", "needs": []}},
    {{"agent": "external", "query": "<what to research on the public web>", "needs": []}}
  ],
  "internal_sources": [
    {{"title": "FAQ PDF", "type": "pdf"}}
  ],
  "external_sources": [
    {{"name": "Standards bodies", "type": "org", "note": "e.g., ISO, NIST"}},
    {{"name": "Peer-reviewed research", "type": "papers", "note": "e.g., arXiv, ACM"}},
    {{"name": "Industry blogs", "type": "web", "note": "e.g., major vendors, cloud providers"}},
    {{"name": "Policy repositories", "type": "web", "note": "e.g., OECD, EU AI Act portals"}}
  ]
}}
"""
    }

    # Keep it deterministic and fast
    raw = chat_completion([system, user], model=GPT_DEPLOYMENT, temperature=0)

    # Parse the two sections
    plan_text = ""
    json_block = "{}"

    # Split by markers
    try:
        # Expecting "PLAN_TEXT:" then a line, then "JSON:" then a JSON block
        parts = raw.split("JSON:")
        left = parts[0] if len(parts) > 0 else ""
        right = parts[1] if len(parts) > 1 else "{}"

        # Extract PLAN_TEXT body after marker
        if "PLAN_TEXT:" in left:
            plan_text = left.split("PLAN_TEXT:")[1].strip()
        else:
            plan_text = left.strip()

        json_block = right.strip()
        parsed = json.loads(json_block)
        steps = parsed.get("steps", [])
        internal_sources = parsed.get("internal_sources", [])
        external_sources = parsed.get("external_sources", [])
    except Exception:
        # Fallback plan text and minimal JSON if parsing fails
        plan_text = (
            f"(1) Define core concepts and scope for {topic}. "
            f"(2) Identify key challenges and risks. "
            f"(3) Review best practices and frameworks. "
            f"(4) Gather case studies. "
            f"(5) Note regulations and standards. "
            f"(6) Compare approaches across sectors. "
            f"(7) Highlight oversight and transparency methods. "
            f"(8) Outline future research directions."
        )
        steps = [
            {"agent": "internal", "query": f"Overview and definitions related to {topic}", "needs": []},
            {"agent": "external", "query": f"Recent developments and risks in {topic}", "needs": []},
            {"agent": "external", "query": f"Best practices, frameworks, and governance for {topic}", "needs": []},
        ]
        internal_sources = [{"title": "FAQ PDF", "type": "pdf"}]
        external_sources = [
            {"name": "Standards bodies", "type": "org", "note": "e.g., ISO, NIST"},
            {"name": "Peer-reviewed research", "type": "papers", "note": "e.g., arXiv, ACM"},
            {"name": "Industry blogs", "type": "web", "note": "e.g., major vendors, cloud providers"},
            {"name": "Policy repositories", "type": "web", "note": "e.g., OECD, EU AI Act portals"},
        ]

    return {
        "topic": topic,
        "plan_text": plan_text,
        "steps": steps,
        "internal_sources": internal_sources,
        "external_sources": external_sources,
    }
