# backend/agents/create_report_agent.py
from backend.services.openai_service import chat_completion
from backend.config import GPT_DEPLOYMENT
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

@dataclass
class Source:
    content: str
    citation: str
    source_type: str  # 'internal' or 'external'
    title: str = ""
    url: str = ""  # Add URL field for external sources

def create_research_report(sources: List[Source], topic: str, max_pages: int = 3, enhanced_rephrasing: bool = False) -> str:
    """
    Creates a comprehensive research report with proper citations and rephrased content.
    """
    
    # Estimate words per page (approximately 300-400 words per page)
    target_words = max_pages * 350
    
    # Prepare content for analysis
    all_content = "\n\n".join([f"Source: {src.citation}\n{src.content}" for src in sources])[:12000]
    
    # Enhanced system prompt for better originality
    originality_instruction = """
    CRITICAL ORIGINALITY AND FORMATTING REQUIREMENTS:
    1. Never copy sentences directly - always rephrase completely
    2. Change sentence structure and word choice significantly
    3. Synthesize information from multiple sources into new insights
    4. Add your own analysis and interpretation
    5. Use synonyms and alternative expressions
    6. Combine related concepts from different sources
    7. Create smooth transitions between ideas
    8. NO MARKDOWN formatting - use plain text only
    9. Use numbered citations [1], [2], etc. consistently
    10. Maintain professional academic tone throughout
    """ if enhanced_rephrasing else ""
    
    # System prompt for comprehensive report generation
    system_prompt = {
        "role": "system",
        "content": f"""You are an expert research report writer. {originality_instruction}
        
        CRITICAL FORMATTING RULES:
        - DO NOT use any markdown (#, ##, ###, *, -, etc.)
        - Use PLAIN TEXT ONLY with proper spacing
        - Section headers should be in ALL CAPS followed by a line of dashes
        - Use numbered citations [1], [2], etc. throughout the text
        - No special characters or formatting symbols
        - Use proper paragraph breaks with double line breaks
        
        Report Structure Requirements:
        - EXECUTIVE SUMMARY (150-200 words)
        - INTRODUCTION (200-250 words) 
        - KEY FINDINGS (400-500 words)
        - ANALYSIS AND IMPLICATIONS (300-400 words)
        - CONCLUSION (150-200 words)
        - REFERENCES section
        
        Citation Rules:
        - Use [1], [2], [3] format for all citations
        - Place citations immediately after relevant statements
        - Ensure every major claim has a citation
        - Use multiple citations for complex points
        """
    }
    
    # Create citation mapping with numbered format
    citation_map, references = format_citations_numbered(sources)
    
    # Prepare sources text for the model
    sources_text = ""
    for i, source in enumerate(sources, 1):
        sources_text += f"\n\nSOURCE {i} [Citation {i}]:\n{source.content[:800]}...\n"
    
    user_prompt = {
        "role": "user",
        "content": f"""Create a comprehensive research report on "{topic}".
        
        Target length: approximately {target_words} words.
        
        CRITICAL REQUIREMENTS:
        - Use PLAIN TEXT only - NO markdown formatting
        - Section headers in ALL CAPS with dashes below
        - Use numbered citations [1], [2], etc. throughout
        - Proper paragraph structure with double line breaks
        - Professional academic writing style
        - Original content that synthesizes the sources
        
        Available Sources ({len(sources)} total):
        {sources_text}
        
        Remember: This must be professionally formatted plain text suitable for Word document conversion.
        """
    }
    
    # Generate the report
    report = chat_completion([system_prompt, user_prompt], model=GPT_DEPLOYMENT, temperature=0.3)
    
    # Post-process to ensure proper formatting
    formatted_report = format_report_professional(report, references, topic)
    
    return formatted_report

def format_citations_numbered(sources: List[Source]) -> Tuple[dict, List[str]]:
    """Create properly formatted numbered academic citations with URLs"""
    
    citation_map = {}
    references = []
    
    for i, source in enumerate(sources, 1):
        citation_key = f"[{i}]"
        
        if source.source_type == 'external':
            # Extract URL from citation or use the citation itself
            url = source.url if source.url else extract_url_from_citation(source.citation)
            title = source.title if source.title else "Web Source"
            
            if url:
                reference = f"[{i}] {title}. Retrieved from {url}"
            else:
                reference = f"[{i}] {title}. External source."
        else:
            # Internal document citation
            doc_name = source.title if source.title else "Internal Document"
            page_info = ""
            if 'p.' in source.citation:
                page_match = re.search(r'p\.(\d+)', source.citation)
                if page_match:
                    page_info = f", p. {page_match.group(1)}"
            
            reference = f"[{i}] {doc_name}{page_info}. Internal company document."
        
        citation_map[i] = citation_key
        references.append(reference)
    
    return citation_map, references

def extract_url_from_citation(citation: str) -> str:
    """Extract URL from citation text"""
    # Remove parentheses and clean up
    cleaned = citation.replace("(", "").replace(")", "").strip()
    
    # Check if it looks like a URL
    if cleaned.startswith(('http://', 'https://', 'www.')):
        return cleaned
    
    # Try to find URL patterns in the text
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, cleaned)
    
    return urls[0] if urls else ""

def format_report_professional(report_text: str, references: List[str], topic: str) -> str:
    """Format the report with proper professional structure and clean formatting."""
    
    # Clean up any markdown formatting that might have slipped through
    report_text = remove_markdown_formatting(report_text)
    
    # Fix section headers to proper format
    report_text = fix_section_headers(report_text)
    
    # Ensure proper citation formatting
    report_text = fix_citation_formatting(report_text)
    
    # Add professional title page
    title_section = f"""{topic.upper()}

Research Report

Generated on: August 11, 2025


"""
    
    # Ensure references section is properly formatted
    if not any(ref_word in report_text.upper() for ref_word in ["REFERENCES", "BIBLIOGRAPHY"]):
        references_section = f"""

REFERENCES
----------------------------------------

{chr(10).join(references)}
"""
        report_text += references_section
    else:
        # Replace existing references with properly formatted ones
        references_section = f"""
REFERENCES
----------------------------------------

{chr(10).join(references)}
"""
        # Find and replace references section
        report_text = re.sub(
            r'REFERENCES.*?(?=\n\n|\Z)', 
            references_section.strip(), 
            report_text, 
            flags=re.DOTALL | re.IGNORECASE
        )
    
    # Final formatting cleanup
    formatted_report = clean_report_formatting(title_section + report_text)
    
    return formatted_report

def remove_markdown_formatting(text: str) -> str:
    """Remove all markdown formatting from text"""
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Remove markdown lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove code blocks
    text = re.sub(r'``````', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    return text

def fix_section_headers(text: str) -> str:
    """Fix section headers to proper ALL CAPS format with dashes"""
    
    # Define section headers and their proper format
    section_patterns = [
        (r'(?i)^executive summary.*?$', 'EXECUTIVE SUMMARY\n----------------------------------------'),
        (r'(?i)^introduction.*?$', 'INTRODUCTION\n----------------------------------------'),
        (r'(?i)^(key findings|main findings).*?$', 'KEY FINDINGS\n----------------------------------------'),
        (r'(?i)^analysis.*?$', 'ANALYSIS AND IMPLICATIONS\n----------------------------------------'),
        (r'(?i)^conclusion.*?$', 'CONCLUSION\n----------------------------------------'),
        (r'(?i)^references.*?$', 'REFERENCES\n----------------------------------------'),
    ]
    
    for pattern, replacement in section_patterns:
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    
    return text

def fix_citation_formatting(text: str) -> str:
    """Ensure consistent citation formatting"""
    
    # Fix spacing around citations
    text = re.sub(r'\s*\[(\d+)\]\s*', r'[\1]', text)
    
    # Ensure citations are properly placed (no double citations)
    text = re.sub(r'\[(\d+)\]\[(\d+)\]', r'[\1][\2]', text)
    
    return text

def clean_report_formatting(text: str) -> str:
    """Clean up overall report formatting"""
    
    # Fix multiple line breaks
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # Ensure proper spacing after section headers
    text = re.sub(r'(----------------------------------------)\n([^\n])', r'\1\n\n\2', text)
    
    # Fix paragraph spacing
    text = re.sub(r'([.!?])\n([A-Z])', r'\1\n\n\2', text)
    
    # Remove extra spaces
    text = re.sub(r' +', ' ', text)
    
    # Clean up line endings
    text = re.sub(r'\n +', '\n', text)
    
    return text.strip()

def ensure_source_diversity(sources: List[Source]) -> List[Source]:
    """Ensure balanced use of internal and external sources"""
    
    internal_sources = [s for s in sources if s.source_type == 'internal']
    external_sources = [s for s in sources if s.source_type == 'external']
    
    # Limit sources per type to ensure variety
    max_per_type = 8
    
    balanced_sources = (
        internal_sources[:max_per_type] + 
        external_sources[:max_per_type]
    )
    
    # Ensure minimum source count
    if len(balanced_sources) < 6:
        logging.warning(f"Only {len(balanced_sources)} sources available. Consider expanding search.")
    
    # Remove duplicate content
    seen_content = set()
    unique_sources = []
    
    for source in balanced_sources:
        content_hash = hash(source.content[:200])  # Use first 200 chars as identifier
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_sources.append(source)
    
    return unique_sources

def validate_content_before_pdf(full_text: str, sources: List[Source]) -> dict:
    """Validate report content quality and originality"""
    
    validation = {
        "word_count": len(full_text.split()),
        "has_citations": bool(re.search(r'\[\d+\]', full_text)),
        "citation_count": len(re.findall(r'\[\d+\]', full_text)),
        "source_utilization": len(set(src.title for src in sources)),
        "sections_present": sum([
            "EXECUTIVE SUMMARY" in full_text,
            "INTRODUCTION" in full_text,
            "CONCLUSION" in full_text,
            "REFERENCES" in full_text
        ]),
        "proper_formatting": sum([
            "----------------------------------------" in full_text,
            not bool(re.search(r'[#*_`]', full_text)),  # No markdown
            bool(re.search(r'EXECUTIVE SUMMARY', full_text))
        ])
    }
    
    # Calculate quality score
    validation["quality_score"] = (
        (validation["word_count"] >= 800) * 0.2 +
        validation["has_citations"] * 0.2 +
        (validation["citation_count"] >= 8) * 0.2 +
        (validation["sections_present"] >= 3) * 0.2 +
        (validation["proper_formatting"] >= 2) * 0.2
    )
    
    return validation


def format_report(report_text: str, references: List[str], topic: str) -> str:
    """Format the report with proper structure and references."""
    
    # Add title page elements
    title_section = f"""
{'='*60}
RESEARCH REPORT

{topic.upper()}

{'='*60}

"""
    
    # Ensure references section is properly formatted
    if "References" not in report_text and "REFERENCES" not in report_text:
        references_section = f"""

REFERENCES
{'-'*20}

{chr(10).join(references)}
"""
        report_text += references_section
    
    # Combine all sections
    final_report = title_section + report_text
    
    return final_report

def validate_report_quality(report: str) -> Dict[str, bool]:
    """Validate the report meets quality requirements."""
    
    checks = {
        "has_citations": bool(re.search(r'\([^)]+\)', report)),
        "has_references": "references" in report.lower(),
        "proper_length": 800 <= len(report.split()) <= 1200,  # 3 pages worth
        "has_structure": any(heading in report.lower() for heading in 
                           ["introduction", "summary", "conclusion", "findings"]),
        "original_content": True  # This would need plagiarism checker integration
    }
    
    return checks

# Enhanced version with section-based generation for better control
def create_detailed_research_report(sources: List[Source], topic: str) -> str:
    """Creates a detailed report by generating each section separately."""
    
    sections = []
    
    # Executive Summary
    exec_summary = generate_section(sources, topic, "executive_summary", 150)
    sections.append(f"EXECUTIVE SUMMARY\n{'-'*20}\n{exec_summary}\n")
    
    # Introduction
    introduction = generate_section(sources, topic, "introduction", 200)
    sections.append(f"INTRODUCTION\n{'-'*20}\n{introduction}\n")
    
    # Main Findings
    findings = generate_section(sources, topic, "findings", 400)
    sections.append(f"KEY FINDINGS\n{'-'*20}\n{findings}\n")
    
    # Analysis
    analysis = generate_section(sources, topic, "analysis", 300)
    sections.append(f"ANALYSIS AND IMPLICATIONS\n{'-'*20}\n{analysis}\n")
    
    # Conclusion
    conclusion = generate_section(sources, topic, "conclusion", 150)
    sections.append(f"CONCLUSION\n{'-'*20}\n{conclusion}\n")
    
    # References
    references = create_references_section(sources)
    sections.append(f"REFERENCES\n{'-'*20}\n{references}")
    
    return f"""
{'='*60}
RESEARCH REPORT: {topic.upper()}
{'='*60}

{''.join(sections)}
"""

def generate_section(sources: List[Source], topic: str, section_type: str, target_words: int) -> str:
    """Generate a specific section of the report."""
    
    section_prompts = {
        "executive_summary": "Provide a concise executive summary highlighting the most critical findings and recommendations.",
        "introduction": "Write an introduction that provides background context and sets up the research topic.",
        "findings": "Detail the main findings from the research, organized thematically with proper citations.",
        "analysis": "Analyze the implications of the findings and provide insights.",
        "conclusion": "Summarize key takeaways and recommendations based on the research."
    }
    
    system_prompt = {
        "role": "system",
        "content": f"""You are writing the {section_type} section of a research report. 
        Requirements:
        - Target length: {target_words} words
        - Include proper citations
        - Rephrase all source material in original language
        - Maintain academic tone
        - {section_prompts[section_type]}"""
    }
    
    content_summary = "\n\n".join([f"[{src.citation}]: {src.content[:500]}..." for src in sources])
    
    user_prompt = {
        "role": "user",
        "content": f"""Write the {section_type} section for a report on "{topic}".
        
        Source materials:
        {content_summary}
        
        Remember to cite sources appropriately and rephrase all content originally."""
    }
    
    return chat_completion([system_prompt, user_prompt], model=GPT_DEPLOYMENT, temperature=0.3)

def create_references_section(sources: List[Source]) -> str:
    """Create properly formatted references section."""
    references = []
    
    for i, source in enumerate(sources, 1):
        if source.source_type == 'external':
            # Format external sources
            ref = f"{i}. {source.title if source.title else 'Web Source'}. Retrieved from {source.citation}"
        else:
            # Format internal sources
            ref = f"{i}. {source.title if source.title else 'Internal Document'}. {source.citation}"
        
        references.append(ref)
    
    return "\n".join(references)

# Usage example:
def example_usage():
    sources = [
        Source(
            content="Your external web content here...",
            citation="https://example.com/article",
            source_type="external",
            title="External Article Title"
        ),
        Source(
            content="Your internal document content here...",
            citation="internal_doc.pdf",
            source_type="internal",
            title="Internal Research Document"
        )
    ]
    
    report = create_research_report(sources, "Your Research Topic", max_pages=3)
    
    # Validate quality
    quality_checks = validate_report_quality(report)
    print("Quality Checks:", quality_checks)
    
    return report
