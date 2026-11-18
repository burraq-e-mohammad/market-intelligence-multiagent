from agents.base_agent import BaseAgent
from tools.news_tool import get_company_news
from typing import Dict, Any, List, Optional
import re

class NewsScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="News Scout",
            role="Lead Market Sentiment & Corporate Event Intelligence Analyst",
            system_prompt="""You are a lead corporate event and market sentiment analyst at an elite financial intelligence firm.
Analyze recent media developments thoroughly. Do NOT write a superficial summary.
You MUST maintain strict consistency with the Single Source of Truth:
1. NEVER cite or hallucinate an outdated or pre-split share price as the current price. The only current price is the verified market quote.
2. For leadership changes (e.g., CEO, Chairman, CFO), report strictly verified announcements. Synthesize leadership transitions accurately without contradiction.
3. FISCAL CALENDAR GROUNDING: Always label quarterly earnings releases using the company's exact fiscal year and quarter schedule supplied in the Verified Market State (e.g. for a late-January FY company, earnings reported in November 2026 are Q3 FY2027, NOT Q4 2026).
4. Regulatory & Geopolitical Risk: In Section 3, explicitly evaluate trade compliance, antitrust inquiries, regulatory probes, or legal oversight.
5. NEGATIVE CONSTRAINT: NEVER use meta words like 'canonical', 'provided', or 'prompt' in your output, and NEVER wrap text or multiples in LaTeX $...$ math delimiters.
Provide an in-depth, structured briefing across 3 clear sections:
### 1. Macro Sentiment & Media Narrative
Diagnose whether coverage is bullish, bearish, or cautiously observant, explaining market tone.
### 2. Key Catalysts, Commercial Deals & Operational Milestones
Highlight specific announcements, customer adoptions, financial disclosures (with exact fiscal quarter labels), or strategic leadership shifts.
### 3. Strategic Risks & Competitive Pressures
Outline emerging risks, market vulnerabilities, export-control or regulatory investigations, and competitor maneuvers."""
        )

    def _infer_llm_sentiment_override(self, llm_text: str, baseline: Dict[str, str]) -> Dict[str, str]:
        """Extract the final tone diagnosed by the News Scout LLM in Section 1 so Executive Summary aligns with it."""
        sec1 = llm_text.split("### 2.")[0] if "### 2." in llm_text else llm_text[:900]
        s_low = sec1.lower()
        if any(p in s_low for p in ["bearish-to-cautiously observant", "bearish to cautiously observant", "bearish-to-cautious"]):
            return {"tone": "Bearish-to-Cautiously Observant", "polarity": "cautious", "rationale": baseline.get("rationale", "")}
        if any(p in s_low for p in ["predominantly bearish", "decidedly bearish", "markedly bearish", "bearish tone", "bearish sentiment"]):
            return {"tone": "Bearish / Risk-Off", "polarity": "cautious", "rationale": baseline.get("rationale", "")}
        if any(p in s_low for p in ["cautiously observant", "cautious", "mixed-to-cautious", "guarded", "volatile"]):
            return {"tone": "Cautiously Observant / Mixed", "polarity": "cautious", "rationale": baseline.get("rationale", "")}
        if any(p in s_low for p in ["constructive", "bullish", "optimistic", "upbeat"]):
            return {"tone": "Constructive / Bullish", "polarity": "positive", "rationale": baseline.get("rationale", "")}
        return baseline

    def analyze(self, company_name: str, symbol: str = "", shared_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        1. Calls the news tool to fetch recent articles for public or private firms.
        2. Reasons through recent events using the LLM with locked verified state & fiscal calendar.
        3. Returns structured sentiment & news summary with dynamically detected events and aligned sentiment pulse.
        """
        tool_result = get_company_news(company_name, symbol=symbol, max_results=6)
        articles: List[Dict[str, str]] = tool_result.get("articles", [])
        detected_events = tool_result.get("detected_events", {})
        baseline_sentiment = tool_result.get("sentiment_pulse", {
            "tone": "Balanced / Observant",
            "polarity": "neutral",
            "rationale": "Recent headlines reflect steady operational coverage."
        })
        
        gov_events = detected_events.get("governance_events", [])
        reg_risks = detected_events.get("regulatory_risks", [])
        comm_milestones = detected_events.get("commercial_milestones", [])

        market_price = shared_state.get("current_price", "") if shared_state else ""
        market_cap = shared_state.get("market_cap", "") if shared_state else ""
        fiscal_cal = (shared_state.get("fiscal_calendar") or {}) if shared_state else {}
        fiscal_summary = fiscal_cal.get("quarter_mapping_summary", "Standard calendar fiscal year.")
        recent_q = fiscal_cal.get("most_recent_reported_quarter", "")

        if not articles:
            return {
                "status": "empty",
                "articles": [],
                "analysis": f"### Market Sentiment Overview\nNo recent breaking media reports discovered for {company_name}.",
                "detected_events": detected_events,
                "sentiment_pulse": baseline_sentiment
            }

        # Format headlines for LLM prompt
        headlines_text = ""
        for i, a in enumerate(articles, 1):
            headlines_text += f"{i}. [{a.get('source')}] {a.get('title')}\n   Date: {a.get('date')}\n   Snippet: {a.get('snippet')}\n"

        prompt = f"""Analyze the recent media stream for {company_name}:

VERIFIED MARKET STATE (SINGLE SOURCE OF TRUTH):
- Current Share Price: {market_price if market_price else 'Refer to verified quote'}
- Market Capitalization: {market_cap if market_cap else 'Refer to verified cap'}
- Fiscal Calendar Grounding: {fiscal_summary}
- Most Recently Completed/Reported Fiscal Quarter: {recent_q if recent_q else 'Refer to filing schedule'}

DYNAMICALLY DETECTED CORPORATE CATALYSTS & RISKS:
- Breaking Governance & Leadership Shifts: {"; ".join(gov_events) if gov_events else 'Standard corporate leadership structure'}
- Regulatory, Antitrust & Compliance Inquiries: {"; ".join(reg_risks) if reg_risks else 'Standard regulatory trade compliance'}
- Commercial & Product Milestones: {"; ".join(comm_milestones) if comm_milestones else 'Active commercial delivery'}
- Baseline Media Pulse: {baseline_sentiment.get('tone')}

VERIFIED NEWS HEADLINES & MEDIA STREAM:
{headlines_text}

CRITICAL CONSISTENCY & FACTUAL DIRECTIVES:
1. Under NO circumstances cite a historical or pre-split share price as the current price. The only current trading price is {market_price}.
2. FISCAL QUARTER ACCURACY: Strictly label any recent earnings release according to the Fiscal Calendar Grounding above ({recent_q if recent_q else 'exact fiscal quarter'}). NEVER confuse calendar quarters with non-calendar fiscal quarters!
3. Leadership Transitions: Accurately synthesize governance. Detail any breaking executive appointments or resignations from the detected catalysts above without misattributing titles from other companies.
4. In Section 3 (Strategic Risks & Competitive Pressures), detail any verified regulatory investigations, export control compliance inquiries, or legal scrutiny identified in the headlines.
5. NEGATIVE CONSTRAINT: NEVER use meta words like 'canonical', 'provided', 'supplied', or 'prompt', and NEVER emit LaTeX math formatting like $P/E^{{**}}$ or $^{{**}}9.72x^{{**}}$.

Format strictly into 3 sections:
### 1. Macro Sentiment & Media Narrative
### 2. Key Catalysts, Commercial Deals & Operational Milestones
### 3. Strategic Risks & Competitive Pressures

Deliver an in-depth, professional briefing."""

        llm_analysis = self.generate_response(prompt)
        
        # Dynamic fallback if in heuristic mode
        if "Report]" in llm_analysis or len(llm_analysis.strip()) < 100:
            tone_label = baseline_sentiment.get("tone", "Balanced / Observant")
            tone_rationale = baseline_sentiment.get("rationale", "Coverage reflects ongoing operational developments.")
            sec1_text = (
                f"Recent media flow around {company_name} reflects a {tone_label.lower()} institutional tone. "
                f"{tone_rationale}"
            )
            
            bullet_points = "; ".join([f"'{a['title']}' ({a['source']})" for a in articles[:3]])
            sec2_text = f"Significant recent coverage highlights key corporate and partner milestones: {bullet_points}."
            if gov_events:
                sec2_text += f"\n\nIn corporate governance, key executive updates include: {'; '.join(gov_events)}."

            sec3_text = (
                f"As industry competition accelerates, primary risk factors center on enterprise budget cycles, "
                f"execution agility, and broader macroeconomic technology trends."
            )
            if reg_risks:
                sec3_text += f"\n\nFrom a regulatory perspective, market observers are monitoring: {'; '.join(reg_risks)}."

            llm_analysis = (
                f"### 1. Macro Sentiment & Media Narrative\n{sec1_text}\n\n"
                f"### 2. Key Catalysts, Commercial Deals & Operational Milestones\n{sec2_text}\n\n"
                f"### 3. Strategic Risks & Competitive Pressures\n{sec3_text}"
            )
            final_sentiment = baseline_sentiment
        else:
            final_sentiment = self._infer_llm_sentiment_override(llm_analysis, baseline_sentiment)

        return {
            "status": "success",
            "articles": articles,
            "analysis": llm_analysis,
            "detected_events": detected_events,
            "sentiment_pulse": final_sentiment
        }
