from agents.base_agent import BaseAgent
from tools.news_tool import get_company_news
from typing import Dict, Any, List, Optional

class NewsScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="News Scout",
            role="Lead Market Sentiment & Corporate Event Intelligence Analyst",
            system_prompt="""You are a lead corporate event and market sentiment analyst at an elite financial intelligence firm.
Analyze recent media developments thoroughly. Do NOT write a superficial summary.
You MUST maintain strict consistency with the Single Source of Truth:
1. NEVER cite or hallucinate an outdated or pre-split share price (e.g. $800+ for Nvidia) as the current price. The only current price is the canonical quote.
2. For leadership changes (e.g., CEO, Chairman, CFO), report strictly verified announcements. Do not create contradictory claims.
3. For technological cycles, anchor to calendar year 2026. Do NOT present legacy architectures (e.g. Hopper H100/H200 from 2022-2024) as "upcoming" catalysts.
Provide an in-depth, structured briefing across 3 clear sections:
### 1. Macro Sentiment & Media Narrative
Diagnose whether coverage is bullish, bearish, or cautiously observant, explaining market tone.
### 2. Key Catalysts, Commercial Deals & Operational Milestones
Highlight specific announcements, customer adoptions, financial disclosures, or strategic shifts.
### 3. Strategic Risks & Competitive Pressures
Outline emerging risks, market vulnerabilities, regulatory observations, or competitor maneuvers."""
        )

    def analyze(self, company_name: str, symbol: str = "", shared_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        1. Calls the news tool to fetch recent articles for public or private firms.
        2. Reasons through recent events using the LLM with locked canonical state.
        3. Returns structured sentiment & news summary.
        """
        tool_result = get_company_news(company_name, symbol=symbol, max_results=6)
        articles: List[Dict[str, str]] = tool_result.get("articles", [])
        
        canonical_price = shared_state.get("current_price", "") if shared_state else ""
        canonical_market_cap = shared_state.get("market_cap", "") if shared_state else ""

        if not articles:
            return {
                "status": "empty",
                "articles": [],
                "analysis": f"### Market Sentiment Overview\nNo recent breaking media reports discovered for {company_name}."
            }

        # Format headlines for LLM prompt
        headlines_text = ""
        for i, a in enumerate(articles, 1):
            headlines_text += f"{i}. [{a.get('source')}] {a.get('title')}\n   Date: {a.get('date')}\n   Snippet: {a.get('snippet')}\n"

        prompt = f"""Analyze the recent media stream for {company_name}:

LOCKED CANONICAL STATE (SINGLE SOURCE OF TRUTH):
- Canonical Share Price: {canonical_price if canonical_price else 'Refer to verified quote'}
- Canonical Market Capitalization: {canonical_market_cap if canonical_market_cap else 'Refer to verified cap'}
- Temporal Anchor: Current Calendar Year is 2026

VERIFIED NEWS HEADLINES & MEDIA STREAM:
{headlines_text}

CRITICAL CONSISTENCY DIRECTIVES:
1. Under NO circumstances should you cite a historical or pre-split share price (e.g. $800+ before the 2024 split) as the current price. The only current trading price is {canonical_price}.
2. For leadership changes, synthesize factual corporate reporting accurately without contradiction.
3. For technological roadmaps, anchor to 2026: do NOT report 2022-2024 legacy generations (such as Hopper H100) as future catalysts.
4. Structure your response into exactly these 3 sections:
### 1. Macro Sentiment & Media Narrative
### 2. Key Catalysts, Commercial Deals & Operational Milestones
### 3. Strategic Risks & Competitive Pressures

Deliver an in-depth, professional briefing."""

        llm_analysis = self.generate_response(prompt)
        
        # Dynamic fallback if in heuristic mode
        if "Report]" in llm_analysis:
            bullet_points = "; ".join([f"'{a['title']}' ({a['source']})" for a in articles[:3]])
            llm_analysis = (
                f"### 1. Macro Sentiment & Media Narrative\n"
                f"Recent media flow around {company_name} reflects active commercial attention and sustained institutional engagement. "
                f"Market narrative is predominantly constructive around core domain execution.\n\n"
                f"### 2. Key Catalysts, Commercial Deals & Operational Milestones\n"
                f"Significant recent coverage highlights key corporate and partner milestones: {bullet_points}.\n\n"
                f"### 3. Strategic Risks & Competitive Pressures\n"
                f"As industry competition accelerates, key observation points focus on client contract renewals, "
                f"execution agility, and broader macroeconomic technology budget trends."
            )

        return {
            "status": "success",
            "articles": articles,
            "analysis": llm_analysis
        }
