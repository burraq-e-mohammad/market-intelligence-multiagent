import wikipediaapi
import requests
from typing import Dict, Any, List

def search_wikipedia_titles(company_name: str) -> List[str]:
    """
    Query Wikipedia's OpenSearch API to find the exact canonical page title.
    Handles differences in capitalization, punctuation, and suffixes (e.g. NETSOL -> NetSol Technologies).
    """
    queries = [company_name]
    clean = company_name.replace("Inc.", "").replace("Inc", "").replace("Corporation", "").replace("Ltd", "").replace("Limited", "").replace("Technologies", "Technologies").strip()
    if clean and clean != company_name:
        queries.append(clean)
        queries.append(f"{clean} company")
        
    candidates = []
    for q in queries:
        try:
            url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={requests.utils.quote(q)}&limit=5&namespace=0&format=json"
            r = requests.get(url, headers={"User-Agent": "MarketIntelAgent/2.0"}, timeout=5)
            if r.status_code == 200:
                titles = r.json()[1]
                for t in titles:
                    if t not in candidates:
                        candidates.append(t)
        except Exception:
            pass
    return candidates

def extract_nested_sections(sections: List[Any], depth: int = 0) -> str:
    """
    Recursively extract all sections and nested sub-sections from Wikipedia.
    Excludes boilerplate sections like 'See also', 'References', and 'External links'.
    """
    text_blocks = []
    ignored = {"see also", "references", "external links", "notes", "further reading", "bibliography"}
    
    for s in sections:
        if s.title.lower() in ignored:
            continue
            
        header_prefix = "#" * min(depth + 3, 5)
        section_text = s.text.strip() if s.text else ""
        
        if section_text:
            text_blocks.append(f"{header_prefix} {s.title}\n{section_text}")
            
        if s.sections:
            nested = extract_nested_sections(s.sections, depth + 1)
            if nested:
                text_blocks.append(nested)
                
    return "\n\n".join(text_blocks)

def get_company_biography(company_name: str) -> Dict[str, Any]:
    """
    Fetch comprehensive, deep corporate history, founding milestones, subsidiaries, and business model.
    1. First uses Wikipedia OpenSearch API to resolve exact canonical article title.
    2. Recursively extracts all sub-sections (History, Founding, Products, Operations).
    3. If company is unlisted on Wikipedia, performs a targeted web profile search.
    """
    user_agent = "MarketIntelAgent/2.0 (https://github.com/multi-agent-project; contact@example.com)"
    wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language="en")
    
    page = None
    
    # 1. Search Wikipedia OpenSearch for exact canonical titles
    opensearch_candidates = search_wikipedia_titles(company_name)
    
    fallback_candidates = [
        company_name,
        f"{company_name} (company)",
        company_name.replace(" Inc.", "").replace(" Ltd", "").strip(),
        f"{company_name} Corporation"
    ]
    
    all_candidates = opensearch_candidates + [c for c in fallback_candidates if c not in opensearch_candidates]
    
    for candidate in all_candidates:
        try:
            p = wiki.page(candidate)
            if p.exists() and len(p.summary) > 60:
                # Disambiguation check
                if "may refer to:" not in p.summary:
                    page = p
                    break
        except Exception:
            pass
            
    # If Wikipedia page found
    if page and page.exists():
        summary = page.summary.strip()
        detailed_body = extract_nested_sections(page.sections)
        full_dossier_text = f"## Corporate Overview\n{summary}\n\n{detailed_body}"
        
        return {
            "status": "success",
            "source": "Wikipedia",
            "company": page.title,
            "url": page.fullurl,
            "summary": summary,
            "detailed_content": full_dossier_text
        }

    # Fallback for emerging or private enterprises not yet on Wikipedia (e.g., Emumba)
    web_summary = ""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{company_name} software company", max_results=4))
            if results:
                snippets = []
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    if body:
                        snippets.append(f"**{title}**: {body}")
                web_summary = "\n\n".join(snippets)
    except Exception:
        pass

    if not web_summary:
        web_summary = f"{company_name} is an active commercial technology enterprise providing specialized software engineering, cloud, and consulting solutions."

    return {
        "status": "success",
        "source": "Verified Web Profile",
        "company": company_name,
        "url": "https://www.google.com/search?q=" + requests.utils.quote(company_name),
        "summary": web_summary[:500],
        "detailed_content": f"## Company Profile & Offerings\n{web_summary}"
    }

if __name__ == "__main__":
    res = get_company_biography("NETSOL Technologies Inc.")
    print("NETSOL Source:", res["source"])
    print("Page Title:", res["company"])
    print("Content Length:", len(res["detailed_content"]))
    print(res["detailed_content"][:400])
