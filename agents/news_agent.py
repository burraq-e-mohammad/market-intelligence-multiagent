from agents.base_agent import BaseAgent
from tools.news_tool import get_company_news
from typing import Dict, Any, List

class NewsScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="News Scout",
            role="Lead Market Sentiment & Corporate Event Intelligence Analyst",
            system_prompt="""You are a lead corporate event and market sentiment analyst at a financial intelligence firm.
Analyze recent media developments thoroughly. Do NOT write a superficial 2-sentence summary.
Provide an in-depth, structured briefing across 3 clear sections:
### 1. Macro Sentiment & Media Narrative
Diagnose whether coverage is bullish, bearish, or cautiously observant, explaining market tone.
### 2. Key Catalysts, Commercial Deals & Operational Milestones
Highlight specific announcements, customer adoptions, financial disclosures, or strategic shifts.
### 3. Strategic Risks & Competitive Pressures
Outline emerging risks, market vulnerabilities, regulatory observations, or competitor maneuvers."""
        )

    def analyze(self, company_name: str, symbol: str = "") -> Dict[str, Any]:
        """
        1. Calls the news tool to fetch recent articles for public or private firms.
        2. Reasons through recent events using the LLM.
        3. Returns structured sentiment & news summary.
        """
        tool_result = get_company_news(company_name, symbol=symbol, max_results=6)
        articles: List[Dict[str, str]] = tool_result.get("articles", [])
        
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

{headlines_text}

Provide an in-depth, structured briefing with these 3 sections:
### 1. Macro Sentiment & Media Narrative
### 2. Key Catalysts, Commercial Deals & Operational Milestones
### 3. Strategic Risks & Competitive Pressures

Quote specific media developments and partner platforms where relevant."""

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
