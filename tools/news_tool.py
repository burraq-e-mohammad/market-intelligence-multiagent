import requests
import xml.etree.ElementTree as ET
import yfinance as yf
from typing import List, Dict, Any, Optional
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
    earnings = []
    
    gov_pattern = re.compile(r'\b(resigns?|stepping down|stepped down|appointed|names?|named|replaces?|interim ceo|new ceo|board chair|chairman|succession|exits?|ousted)\b', re.IGNORECASE)
    reg_pattern = re.compile(r'\b(investigation|probe|inquiry|sec|doj|export control|sanctions|subpoena|antitrust|lawsuit|penalty|fine|oversight committee|compliance|scrutiny)\b', re.IGNORECASE)
    comm_pattern = re.compile(r'\b(launches|unveils|next-gen|record revenue|earnings beat|acquisition|partnership|deal|contracts?|breakthrough)\b', re.IGNORECASE)
    earn_pattern = re.compile(r'\b(earnings|quarterly revenue|eps|guidance|beats? estimates|tops? estimates|after[- ]hours|revenue of \$|q[1-4]\s*(?:fy)?20\d{2})\b', re.IGNORECASE)

    for a in articles:
        text = f"{a.get('title', '')} {a.get('snippet', '')}"
        if gov_pattern.search(text):
            governance.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")
        if reg_pattern.search(text):
            regulatory.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")
        if comm_pattern.search(text):
            commercial.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")
        if earn_pattern.search(text):
            earnings.append(f"{a.get('title')} ({a.get('source')}, {a.get('date')})")

    return {
        "governance_events": governance[:4],
        "regulatory_risks": regulatory[:4],
        "commercial_milestones": commercial[:4],
        "earnings_disclosures": earnings[:4]
    }

def compute_sentiment_pulse(articles: List[Dict[str, str]], detected_events: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Deterministically computes the baseline media sentiment tone from live headlines and detected catalysts.
    Ensures cross-section tone alignment between Executive Summary and News Sentiment sections.
    """
    if not articles:
        return {
            "tone": "Neutral / Observant",
            "polarity": "neutral",
            "rationale": "Media coverage is sparse or balanced without major directional catalysts."
        }

    neg_pat = re.compile(
        r'\b(resigns?|stepped down|scandal|fiasco|probe|investigation|inquiry|lawsuit|antitrust|'
        r'sanctions?|export control|plunge[sd]?|drop[sp]?|slump[sd]?|tumble[sd]?|downgrade[sd]?|'
        r'miss(?:es|ed)?|warning|concern[s]?|scrutiny|risk[s]?|ousted|volatility|bearish|sell-off)\b',
        re.IGNORECASE
    )
    pos_pat = re.compile(
        r'\b(beat[s]?|surge[sd]?|record|rally|rallies|upgrade[sd]?|outperform|breakthrough|'
        r'partnership|launch(?:es|ed)?|strong demand|bullish|soar[sd]?|tops estimates|exceeds)\b',
        re.IGNORECASE
    )

    neg_hits = 0
    pos_hits = 0
    for a in articles:
        text = f"{a.get('title', '')} {a.get('snippet', '')}"
        neg_hits += len(neg_pat.findall(text))
        pos_hits += len(pos_pat.findall(text))

    has_gov_shock = bool(detected_events.get("governance_events"))
    has_reg_risk = bool(detected_events.get("regulatory_risks"))

    if neg_hits >= pos_hits + 2 or (has_gov_shock and has_reg_risk and neg_hits >= pos_hits):
        return {
            "tone": "Bearish-to-Cautiously Observant",
            "polarity": "cautious",
            "rationale": "Media coverage highlights acute governance transitions, regulatory scrutiny, or headline volatility outweighing operational momentum."
        }
    elif has_gov_shock or has_reg_risk or neg_hits > pos_hits:
        return {
            "tone": "Mixed-to-Cautiously Observant",
            "polarity": "cautious",
            "rationale": "Institutional coverage balances commercial execution against active governance or regulatory risk overhangs."
        }
    elif pos_hits > neg_hits:
        return {
            "tone": "Constructive / Bullish",
            "polarity": "positive",
            "rationale": "Media narrative emphasizes commercial wins, product execution, and positive earnings momentum."
        }
    return {
        "tone": "Balanced / Observant",
        "polarity": "neutral",
        "rationale": "Recent headlines reflect steady operational coverage without extreme directional skew."
    }

def build_anchored_news_query(
    clean_name: str,
    symbol: str = "",
    resolved_entity: Optional[Dict[str, Any]] = None,
    recency: str = "when:30d"
) -> str:
    """
    Construct a strict boolean Google News query using ResolvedEntity anchors,
    negative keyword exclusions, and recency window.
    Prevents bare single-word queries like 'Motive', 'Jazz', or 'Zong' from matching
    common English nouns, true-crime stories, NBA teams, music, or 1781 ships.
    """
    trade = (resolved_entity.get("trade_name") or clean_name).strip() if resolved_entity else clean_name
    trade_low = trade.lower()
    raw_anchors = list(resolved_entity.get("required_search_anchors") or []) if resolved_entity else []
    negatives = list(resolved_entity.get("negative_keywords") or []) if resolved_entity else []

    # Filter out bare trade name itself from anchors so ("Brand" AND ("Brand" OR ...)) NEVER collapses to bare "Brand"!
    distinct_anchors = [a.strip() for a in raw_anchors if a and a.strip().lower() != trade_low]

    if resolved_entity and distinct_anchors:
        # Separate standalone strong brand aliases from contextual domain keywords
        strong_aliases = []
        context_anchors = []
        for a in distinct_anchors:
            a_low = a.lower()
            is_brand_alias = (
                (trade_low in a_low and len(a.split()) >= 2)
                or (a.isupper() and 2 <= len(a) <= 6 and a_low not in ("ipo", "ceo", "cfo", "sec", "coo", "cto"))
            )
            if is_brand_alias and len(strong_aliases) < 3:
                strong_aliases.append(f'"{a}"' if " " in a else a)
            else:
                context_anchors.append(f'"{a}"' if " " in a else a)

        if not context_anchors:
            # Fall back to sector / HQ tokens so ("Trade" AND (...)) is strictly anchored
            hq = (resolved_entity.get("headquarters") or "").split(",")[-1].strip()
            sec = (resolved_entity.get("sector") or "").split("&")[0].strip()
            if sec and sec.lower() != trade_low:
                context_anchors.append(f'"{sec}"' if " " in sec else sec)
            if hq and hq.lower() not in ("global", trade_low):
                context_anchors.append(f'"{hq}"' if " " in hq else hq)
            if not context_anchors:
                context_anchors = ["company", "enterprise", "industry", "revenue", "commercial"]

        trade_clause = f'("{trade}" AND ({" OR ".join(context_anchors[:5])}))'
        if strong_aliases:
            base = f'({" OR ".join(strong_aliases)} OR {trade_clause})'
        else:
            base = trade_clause
    else:
        if len(clean_name.split()) == 1 and (not symbol or symbol == "PRIVATE / UNLISTED"):
            # Never search a bare single-word dictionary name without corporate anchors
            base = f'("{clean_name}" AND (company OR startup OR software OR earnings OR revenue OR IPO OR funding))'
        else:
            base = f'"{clean_name}"'
            if symbol and symbol != "PRIVATE / UNLISTED":
                clean_sym = symbol.split(".")[0]
                base += f' OR "{symbol}"'
                if len(clean_sym) >= 3:
                    base += f' OR "{clean_sym}"'
            base = f'({base})'

    # Append negative exclusions (e.g. -"possible motive" -"Jazz Pharmaceuticals" -"Utah Jazz" -NBA)
    neg_clauses = []
    for neg in negatives[:10]:
        n_clean = neg.strip()
        if not n_clean:
            continue
        neg_clauses.append(f'-"{n_clean}"' if " " in n_clean else f'-{n_clean}')

    parts = [base] + neg_clauses
    if recency:
        parts.append(recency)
    return " ".join(parts)

def is_relevant_article(
    title: str,
    snippet: str,
    clean_name: str,
    symbol: str = "",
    resolved_entity: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Strict pre-synthesis relevance filter:
    1. Hard-drops any article containing negative keywords (e.g. possible motive, home invasion, Utah Jazz, slave ship).
    2. Guards common English dictionary words & single-word brand names against true-crime, tabloid, and noun-phrase collisions.
    3. Drops tangential viral soundbites without material policy/business substance.
    4. Verifies entity match AND (for ambiguous/single-word/subsidiary entities) genuine domain/anchor match.
    """
    combined = f"{title} {snippet}".lower()
    title_lower = title.lower()
    clean_name_lower = clean_name.lower()
    clean_sym = symbol.split(".")[0].lower() if (symbol and symbol != "PRIVATE / UNLISTED") else ""
    trade_lower = (resolved_entity.get("trade_name") or clean_name).lower().strip() if resolved_entity else clean_name_lower
    canonical_lower = (resolved_entity.get("canonical_name") or clean_name).lower().strip() if resolved_entity else clean_name_lower
    anchors_lower = [a.lower().strip() for a in (resolved_entity.get("required_search_anchors") or []) if a and a.strip().lower() != trade_lower] if resolved_entity else []

    # 1. Hard negative-keyword exclusion (supports both single words and multi-word phrases)
    if resolved_entity:
        for neg in (resolved_entity.get("negative_keywords") or []):
            n_low = neg.lower().strip()
            if len(n_low) >= 3 and re.search(rf'\b{re.escape(n_low)}\b', combined):
                return False

    # 2. Universal Common-Noun & Violent-Crime / Tabloid Collision Guard for single-word brand names
    # Prevents e.g. "Toronto Police Discuss Possible Motive Behind 'Brutal' Home Invasion and Hammer Attack on CEO Family - People.com"
    is_single_word_brand = len(trade_lower.split()) == 1
    strong_brand_present = (
        (canonical_lower != trade_lower and len(canonical_lower) > len(trade_lower) + 2 and canonical_lower.split(",")[0].strip() in combined)
        or (clean_sym and len(clean_sym) >= 3 and bool(re.search(rf'\b{re.escape(clean_sym)}\b', combined)))
        or any(
            (trade_lower in a and len(a.split()) >= 2 and a in combined)
            or (len(a) >= 4 and a in combined)
            for a in anchors_lower
        )
    )

    if is_single_word_brand and not strong_brand_present:
        # 2a. Reject common-noun English idioms where the brand word is clearly used as an ordinary noun (not a company)
        noun_idiom_pat = re.compile(
            rf'\b(?:possible|ulterior|profit|hidden|clear|primary|real|true|secret|political|alleged|suspected|unknown|no|any|his|her|their|the|a)\s+{re.escape(trade_lower)}\b'
            rf'|\b{re.escape(trade_lower)}\s+(?:behind|for|in\s+the|of\s+the|to\s+kill|unknown)\b',
            re.IGNORECASE
        )
        if noun_idiom_pat.search(title) or noun_idiom_pat.search(combined):
            return False

        # 2b. Reject violent crime / police / tabloid stories that accidentally mention a generic word + "CEO"
        crime_tabloid_pat = re.compile(
            r'\b(home\s+invasion|hammer\s+attack|murder|homicide|manslaughter|shooting|stabbing|assault\s+on|'
            r'police\s+discuss|police\s+investigate|police\s+say|suspect\s+arrested|arrested\s+for|'
            r'brutal\s+attack|true\s+crime|people\.com|tmz|daily\s+mail)\b',
            re.IGNORECASE
        )
        if crime_tabloid_pat.search(combined):
            return False

    # 3. Skip non-material viral political soundbites / tangential gossip
    is_material_policy = bool(re.search(r'\b(tariff|antitrust|doj|ftc|sec|eu|dma|probe|lawsuit|export|sanction|ban|fine|settlement|regulator|pta|spectrum|5g)\b', title_lower))
    is_tangential_soundbite = bool(re.search(r'\b(should\s+replace|is\s+[\'"]?a\s+legend[\'"]?|calls\s+[\w\s]+\s+a\s+legend|mistakenly\s+calls|gaffe|quips|obituary)\b', title_lower))
    if is_tangential_soundbite and not is_material_policy:
        return False

    # 4. Positive entity + anchor/sector/geography match
    mentions_entity = (
        clean_name_lower in combined
        or bool(re.search(rf'\b{re.escape(trade_lower)}\b', combined))
        or (clean_sym and len(clean_sym) >= 3 and bool(re.search(rf'\b{re.escape(clean_sym)}\b', combined)))
        or any(a in combined for a in anchors_lower[:3])
    )
    if not mentions_entity:
        return False

    # For short/single-word names or subsidiaries, require at least one genuine domain/business/anchor hit!
    # Note: NEVER include generic non-company words like "ceo" alone here (crime stories can mention a victim "CEO").
    if resolved_entity and (resolved_entity.get("entity_type") == "SUBSIDIARY" or is_single_word_brand):
        hq_tokens = [t.strip().lower() for t in re.split(r'[,\s]+', resolved_entity.get("headquarters", "")) if len(t.strip()) >= 3 and t.strip().lower() not in ("global", "san")]
        sector_tokens = [t.strip().lower() for t in re.split(r'[\s,&/\-]+', resolved_entity.get("sector", "")) if len(t.strip()) >= 4 and t.strip().lower() not in ("services", "commercial", "solutions", "physical", "operations", "management")]
        parent_tokens = [t.strip().lower() for t in re.split(r'[\s\(\):,\-]+', resolved_entity.get("parent_company") or "") if len(t.strip()) >= 4 and t.strip().lower() not in ("limited", "ltd", "nasdaq", "sehk", "group")]
        corp_signals = ["earnings", "revenue", "ipo", "s-1", "funding", "valuation", "acquisition", "quarterly", "software", "platform", "enterprise", "ai ", "dashcam", "telematics", "fleet", "saas", "lawsuit", "patent"]
        if resolved_entity.get("entity_type") == "SUBSIDIARY":
            corp_signals.extend(["telecom", "4g", "5g", "broadband", "subscriber", "fintech", "pta"])
        domain_pool = set(anchors_lower + hq_tokens + sector_tokens + parent_tokens + corp_signals)
        # Exclude bare trade name itself from domain_pool so 'Motive' or 'Jazz' alone isn't enough!
        domain_pool.discard(trade_lower)
        if domain_pool and not any(tok in combined for tok in domain_pool):
            return False

    return True

def _fetch_google_rss_stream(
    query_terms: str,
    clean_name: str,
    symbol: str,
    limit: int,
    existing_titles: set,
    resolved_entity: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Helper to query a targeted Google News RSS stream with strict entity relevance filtering."""
    fetched: List[Dict[str, str]] = []
    try:
        encoded_query = requests.utils.quote(query_terms)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(rss_url, headers=headers, timeout=8)
        if response.status_code != 200:
            return fetched
        root = ET.fromstring(response.content)

        for item in root.findall(".//item"):
            if len(fetched) >= limit:
                break
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else "Recent"
            source_elem = item.find("source")
            source_name = source_elem.text if source_elem is not None else "News Source"
            desc_elem = item.find("description")
            raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else title
            clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc)
            clean_desc = " ".join(clean_desc.split())[:280]

            if is_relevant_article(title, clean_desc, clean_name, symbol=symbol, resolved_entity=resolved_entity):
                if title and title not in existing_titles:
                    existing_titles.add(title)
                    fetched.append({
                        "title": title,
                        "source": source_name,
                        "date": pub_date,
                        "snippet": clean_desc or title,
                        "url": link
                    })
    except Exception:
        pass
    return fetched

def get_company_news(
    company_name: str,
    symbol: str = "",
    max_results: int = 8,
    resolved_entity: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetch verified breaking news for the exact ResolvedEntity using anchored boolean RSS queries,
    negative keyword exclusions, strict recency filtering, and post-fetch relevance gating.
    """
    articles: List[Dict[str, str]] = []
    seen_titles: set = set()
    clean_name = company_name.strip()

    # 1a. High-signal stream (30-day recency, boolean anchors & negative exclusions)
    base_30d = build_anchored_news_query(clean_name, symbol=symbol, resolved_entity=resolved_entity, recency="when:30d")
    catalyst_query = f'{base_30d} (earnings OR revenue OR IPO OR "S-1" OR funding OR acquisition OR partnership OR lawsuit OR launch OR guidance OR 5G OR spectrum)'
    articles.extend(_fetch_google_rss_stream(catalyst_query, clean_name, symbol, limit=max(4, max_results // 2), existing_titles=seen_titles, resolved_entity=resolved_entity))

    # 1b. General anchored breaking headlines stream (30-day recency)
    remaining = max(0, max_results - len(articles))
    if remaining > 0:
        articles.extend(_fetch_google_rss_stream(base_30d, clean_name, symbol, limit=remaining, existing_titles=seen_titles, resolved_entity=resolved_entity))

    # 1c. If fewer than 2 articles in last 30d (common for regional subsidiaries), widen cleanly to 180d with same strict anchors
    if len(articles) < 2:
        base_180d = build_anchored_news_query(clean_name, symbol=symbol, resolved_entity=resolved_entity, recency="when:180d")
        articles.extend(_fetch_google_rss_stream(base_180d, clean_name, symbol, limit=max_results - len(articles), existing_titles=seen_titles, resolved_entity=resolved_entity))

    # 2. Secondary: If public stock symbol is present (and NOT a subsidiary without its own ticker), add yfinance news
    is_subsidiary = resolved_entity and resolved_entity.get("entity_type") == "SUBSIDIARY"
    if not is_subsidiary and len(articles) < max_results and symbol and symbol != "PRIVATE / UNLISTED":
        try:
            from tools.finance_tool import get_yf_session
            ticker = yf.Ticker(symbol, session=get_yf_session())
            for item in (ticker.news or [])[:max_results]:
                if len(articles) >= max_results:
                    break
                content = item.get("content", {})
                title = content.get("title") or item.get("title")
                summary = content.get("summary") or item.get("description") or ""
                provider = content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else "Yahoo Finance"
                url = content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else item.get("link", "")
                pub_date = content.get("pubDate") or "Recent"
                
                if title and title not in seen_titles and is_relevant_article(title, summary, clean_name, symbol=symbol, resolved_entity=resolved_entity):
                    seen_titles.add(title)
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
    sentiment_pulse = compute_sentiment_pulse(articles, detected_events)

    return {
        "status": "success" if articles else "empty",
        "company": company_name,
        "count": len(articles),
        "articles": articles,
        "detected_events": detected_events,
        "sentiment_pulse": sentiment_pulse
    }

if __name__ == "__main__":
    import json
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else input("Enter a company name or ticker: ").strip()
    if target:
        print(json.dumps(get_company_news(target, max_results=3), indent=2))
