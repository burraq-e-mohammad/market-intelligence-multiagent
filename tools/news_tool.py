import requests
import xml.etree.ElementTree as ET
import yfinance as yf
from typing import List, Dict, Any
import re

def classify_breaking_events(articles: List[Dict[str, str]]) -> Dict[str, List[str]]:
    """
    Dynamically analyzes news headlines and snippets for high-priority corporate catalysts across ANY company:
    1. Governance & Leadership transitions (resignations, appointments, interim leaders, board changes)
    2. Regulatory, legal & antitrust actions (DOJ, SEC, export controls, sanctions, subpoenas, investigations)
    3. Commercial, technological & M&A milestones
    """
    governance = []
    regulatory = []
    commercial = []
    
    gov_pattern = re.compile(r'\b(resigns?|stepping down|stepped down|appointed|names?|named|replaces?|interim ceo|new ceo|board chair|chairman|succession|exits?|ousted)\b', re.IGNORECASE)
    reg_pattern = re.compile(r'\b(investigation|probe|inquiry|sec|doj|export control|sanctions|subpoena|antitrust|lawsuit|penalty|fine|oversight committee|compliance|scrutiny)\b', re.IGNORECASE)
    comm_pattern = re.compile(r'\b(launches|unveils|next-gen|record revenue|earnings beat|acquisition|partnership|deal|contracts?|breakthrough)\b', re.IGNORECASE)

    for a in articles:
        text = f"{a.get('title', '')} {a.get('snippet', '')}"
        if gov_pattern.search(text):
            governance.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")
        if reg_pattern.search(text):
            regulatory.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")
        if comm_pattern.search(text):
            commercial.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")

    return {
        "governance_events": governance[:3],
        "regulatory_risks": regulatory[:3],
        "commercial_milestones": commercial[:3]
    }

def get_company_news(company_name: str, symbol: str = "", max_results: int = 5) -> Dict[str, Any]:
    """
    Fetch verified breaking news for the exact target company.
    Uses strict exact phrase quotes and ticker search to prevent matching unrelated companies.
    """
    articles: List[Dict[str, str]] = []
    clean_name = company_name.strip()
    
    # 1. Primary: Targeted Google News RSS feed using exact phrase quoting
    try:
        # Build strict search query
        query_terms = f'"{clean_name}"'
        if symbol and symbol != "PRIVATE / UNLISTED":
            clean_sym = symbol.split(".")[0] # e.g. SYS from SYS.KA
            query_terms += f' OR "{symbol}"'
            if len(clean_sym) >= 3:
                query_terms += f' OR "{clean_sym}"'
                
        encoded_query = requests.utils.quote(query_terms)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(rss_url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                if len(articles) >= max_results:
                    break
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else "Recent"
                source_elem = item.find("source")
                source_name = source_elem.text if source_elem is not None else "News Source"
                
                # Verify that title actually mentions the company name or clean symbol
                # and reject false prefixes (e.g. reject 'TD Power Systems' if searching 'Systems Limited')
                title_lower = title.lower()
                clean_name_lower = clean_name.lower()
                
                # Check relevance
                if clean_name_lower in title_lower or (symbol and symbol.lower() in title_lower):
                    # Filter out false prefix entities (e.g. 'Concord Enviro Systems Limited' or 'TD Power Systems Limited')
                    m = re.search(r'([A-Za-z0-9]+)\s+Systems\s+Limited', title, re.IGNORECASE)
                    if m and clean_name_lower == "systems limited":
                        prev_word = m.group(1).lower()
                        if prev_word not in ['the', 'at', 'in', 'of', 'for', 'about', 'and', 'from', 'with', 'to']:
                            continue
                            
                    if title and not any(a["title"] == title for a in articles):
                        articles.append({
                            "title": title,
                            "source": source_name,
                            "date": pub_date,
                            "snippet": title,
                            "url": link
                        })
    except Exception:
        pass

    # 2. Secondary: If public stock symbol is present, add ticker-specific news from yfinance
    if len(articles) < max_results and symbol and symbol != "PRIVATE / UNLISTED":
        try:
            ticker = yf.Ticker(symbol)
            for item in (ticker.news or [])[:max_results]:
                if len(articles) >= max_results:
                    break
                content = item.get("content", {})
                title = content.get("title") or item.get("title")
                summary = content.get("summary") or item.get("description") or ""
                provider = content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else "Yahoo Finance"
                url = content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else item.get("link", "")
                pub_date = content.get("pubDate") or "Recent"
                
                if title and not any(a["title"] == title for a in articles):
                    articles.append({
                        "title": title,
                        "source": provider,
                        "date": str(pub_date),
                        "snippet": summary,
                        "url": url or ""
                    })
        except Exception:
            pass

    detected_events = classify_breaking_events(articles)

    return {
        "status": "success" if articles else "empty",
        "company": company_name,
        "count": len(articles),
        "articles": articles,
        "detected_events": detected_events
    }

if __name__ == "__main__":
    import json
    print(json.dumps(get_company_news("Systems Limited", symbol="SYS.KA", max_results=3), indent=2))
