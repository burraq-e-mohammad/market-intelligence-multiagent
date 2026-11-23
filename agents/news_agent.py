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
        resolved_entity = (shared_state.get("resolved_entity") or None) if shared_state else None
        display_name = (resolved_entity.get("canonical_name") if resolved_entity else None) or company_name
        tool_result = get_company_news(display_name, symbol=symbol, max_results=8, resolved_entity=resolved_entity)
        articles: List[Dict[str, str]] = tool_result.get("articles", [])
        detected_events = tool_result.get("detected_events", {})
        baseline_sentiment = tool_result.get("sentiment_pulse", {
            "tone": "Balanced / Observant",
            "polarity": "neutral",
            "rationale": "Recent headlines reflect steady operational coverage."
        })
        
        # Merge shared_state corporate governance/regulatory events with live RSS detections
        # Prevents Section 5.2 from contradicting Sections 2 & 3 when RSS focuses on earnings/ETFs!
        shared_gov = (shared_state.get("breaking_governance") or []) if shared_state else []
        shared_reg = (shared_state.get("breaking_regulatory") or []) if shared_state else []
        verified_officers = (shared_state.get("verified_leadership") or []) if shared_state else []

        gov_events = list(dict.fromkeys(shared_gov + (detected_events.get("governance_events") or [])))
        reg_risks = list(dict.fromkeys(shared_reg + (detected_events.get("regulatory_risks") or [])))
        comm_milestones = detected_events.get("commercial_milestones", [])
        earnings_disclosures = detected_events.get("earnings_disclosures", [])

        market_price = shared_state.get("current_price", "") if shared_state else ""
        extended_hours = (shared_state.get("metrics", {}).get("extended_hours_context", "") if shared_state else "")
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
- Current Regular-Session Share Price: {market_price if market_price else 'Refer to verified quote'}
- Extended-Hours Trading Context: {extended_hours if extended_hours else 'Regular session close (no active after-hours feed delta)'}
- Market Capitalization: {market_cap if market_cap else 'Refer to verified cap'}
- Verified Active Leadership: {", ".join(verified_officers) if verified_officers else 'Documented corporate officers'}
- Fiscal Calendar Grounding: {fiscal_summary}
- Most Recently Completed/Reported Fiscal Quarter: {recent_q if recent_q else 'Refer to filing schedule'}

DYNAMICALLY DETECTED CORPORATE CATALYSTS & RISKS:
- Verified Governance & Leadership Shifts: {"; ".join(gov_events) if gov_events else 'No new governance filings beyond documented leadership profile'}
- Regulatory, Antitrust & Compliance Inquiries: {"; ".join(reg_risks) if reg_risks else 'Standard regulatory trade compliance'}
- Post-Earnings Disclosures & Guidance: {"; ".join(earnings_disclosures) if earnings_disclosures else 'Refer to verified headlines below'}
- Commercial & Product Milestones: {"; ".join(comm_milestones) if comm_milestones else 'Active commercial delivery'}
- Baseline Media Pulse: {baseline_sentiment.get('tone')}

VERIFIED NEWS HEADLINES & MEDIA STREAM:
{headlines_text}

CRITICAL CONSISTENCY & FACTUAL DIRECTIVES:
1. SOURCE-ONLY RULE: Do not infer causes, votes, executive reinstatement, political endorsements, or 28% price moves unless the headline or snippet explicitly states them. If a detail is not in the supplied source, omit it.
2. CONFIRM SOURCE LIMIT: A headline may be sensational or speculative. Treat it only as a reported claim, with the publisher and date. Do not convert a headline into a confirmed corporate action or market outcome.
1. PRICE & EXTENDED HOURS: Never cite a historical pre-split share price as current. Regular-session price is {market_price}. If Extended-Hours Trading Context or post-earnings headlines report an after-hours/pre-market move, explicitly cite that extended-hours context alongside the regular close.
2. CONCRETE ACTUALS, NUMERICAL ATTRIBUTION & CROSS-BORDER CURRENCY CLARITY: Whenever headlines/snippets contain concrete reported earnings numbers (quarterly revenue, EPS, beat, guidance) or investment figures, cite those exact numbers faithfully. NEVER conflate or double-count dollar amounts across separate geographies or sub-projects. If a translated/regional headline quotes a foreign partner's or competitor's revenue in local currency (e.g. a US firm's revenue converted to KRW/JPY trillions by regional press), explicitly note that it is a local-currency equivalent (or cite their native USD figure) rather than implying a foreign company reports natively in local currency.
3. FISCAL QUARTER ACCURACY: Strictly label any recent earnings release according to the Fiscal Calendar Grounding above ({recent_q if recent_q else 'exact fiscal quarter'}). NEVER confuse calendar quarters with non-calendar fiscal quarters!
4. CROSS-SECTION LEADERSHIP COHESION: Accurately reflect Verified Governance & Leadership Shifts above. If an executive transition occurred (e.g., resignation or Interim CEO appointment), NEVER claim that 'governance structures remain stable without disruptive executive transitions'!
5. In Section 3 (Strategic Risks & Competitive Pressures), detail any verified regulatory investigations, export control compliance inquiries, or legal scrutiny identified above.
6. FORMATTING & NEGATIVE CONSTRAINT: NEVER escape dollar signs with backslashes (write $3.75T, NEVER \\$3.75T). NEVER wrap text or ratios in LaTeX $...$ math delimiters (write P/E and 9.72x in plain text). NEVER use meta words like 'canonical', 'provided', 'supplied', or 'prompt'.

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
                sec2_text += f"\n\nIn corporate governance, key executive updates include: {'; '.join(g.rstrip('. ') for g in gov_events)}."

            sec3_text = (
                f"As industry competition accelerates, primary risks should remain company-specific, including "
                f"execution, supply-chain continuity, regulatory exposure, and competitive positioning."
            )
            if reg_risks:
                sec3_text += f"\n\nFrom a regulatory perspective, market observers are monitoring: {'; '.join(r.rstrip('. ') for r in reg_risks)}."

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
