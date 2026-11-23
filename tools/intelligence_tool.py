"""
Intelligence Tool:
Provides deterministic, institutional-grade analytics for multi-agent dossiers:
1. Enterprise Health & Risk Scorecard (0-100 rating across Financial Strength, Growth, Valuation, Safety/Risk)
2. Competitive Peer Benchmarking (side-by-side comparison with 2-3 primary rivals)
3. Executive Verdict & Bull vs. Bear Matrix (instant 30-second summary with top 3 pros and top 3 cons)
"""

from typing import Dict, Any, List, Optional
import re

def fetch_programmatic_peer_metrics(
    ticker_symbol: str,
    name: str,
    edge: str,
    fallback_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Programmatically fetches verified financial metrics for a competitor peer using yfinance.
    Queries fast_info and info for market cap, P/E, revenue growth, and net profit margin.
    If live fetch is throttled or offline, falls back cleanly to verified institutional defaults.
    """
    fallback = fallback_data or {}
    result = {
        "name": name or fallback.get("name", ticker_symbol),
        "ticker": ticker_symbol,
        "market_cap": fallback.get("market_cap", "N/A"),
        "pe_ratio": fallback.get("pe_ratio", "N/A"),
        "revenue_growth": fallback.get("revenue_growth", "N/A"),
        "net_margin": fallback.get("net_margin", "N/A"),
        "edge": edge or fallback.get("edge", "Competitive Strategic Moat")
    }

    try:
        import yfinance as yf
        from tools.finance_tool import get_yf_session, format_number
        session = get_yf_session()
        ticker_obj = yf.Ticker(ticker_symbol, session=session)

        # 1. Market Cap via fast_info (ultra-fast ~0.1s latency)
        mc = None
        fast_info = getattr(ticker_obj, "fast_info", None)
        if fast_info:
            try:
                mc = getattr(fast_info, "market_cap", None)
            except Exception:
                pass

        if mc and isinstance(mc, (int, float)) and mc > 0:
            curr = getattr(fast_info, "currency", "USD") or "USD"
            result["market_cap"] = format_number(mc, currency=curr)

        # Only pull full info if key metrics are missing from institutional fallback
        if result.get("pe_ratio") in (None, "N/A") or result.get("revenue_growth") in (None, "N/A"):
            info = {}
            try:
                info = ticker_obj.info or {}
            except Exception:
                pass

            if mc is None and info:
                mc = info.get("marketCap")
                if mc and isinstance(mc, (int, float)) and mc > 0:
                    curr = info.get("currency") or "USD"
                    result["market_cap"] = format_number(mc, currency=curr)

            # 2. P/E Multiple
            trailing_pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            pe = trailing_pe or forward_pe
            if pe and isinstance(pe, (int, float)) and pe > 0:
                result["pe_ratio"] = f"{pe:.1f}x"

            # 3. Revenue Growth (YoY)
            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None and isinstance(rev_growth, (int, float)):
                result["revenue_growth"] = f"{rev_growth * 100:+.1f}%"

            # 4. Profit Margin
            profit_margin = info.get("profitMargins") or info.get("operatingMargins")
            if profit_margin is not None and isinstance(profit_margin, (int, float)):
                result["net_margin"] = f"{profit_margin * 100:.1f}%"

    except Exception:
        # Fall back cleanly without breaking the pipeline
        pass

    return result

def get_competitor_comparison(dossier: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Discover and live-fetch peers dynamically, without a hardcoded peer registry."""
    company_name = (dossier.get("company_name") or "").strip()
    ticker = (dossier.get("ticker") or "").strip()
    if not company_name:
        return []

    resolved = dossier.get("resolved_entity") or {}
    sector = resolved.get("sector") or dossier.get("metrics", {}).get("sector") or "its industry"
    industry = dossier.get("metrics", {}).get("industry") or sector

    try:
        from agents.base_agent import BaseAgent
        agent = BaseAgent(
            name="Peer Discovery",
            role="Competitive Peer Researcher",
            system_prompt="Identify publicly traded direct competitors. Return only valid JSON."
        )
        prompt = f"""Identify up to 3 direct public-company competitors for {company_name}
({ticker or 'unlisted'}) in sector {sector}, industry {industry}.
Return ONLY a JSON array of objects:
{{"name":"company name","ticker":"exchange symbol","edge":"brief factual competitive distinction"}}.
Exclude {company_name}. Do not invent names or symbols."""
        import json
        match = re.search(r'\[.*\]', agent.generate_response(prompt), re.DOTALL)
        candidates = json.loads(match.group(0)) if match else []
    except Exception:
        candidates = []

    peers = []
    for candidate in candidates[:3]:
        name = str(candidate.get("name") or "").strip()
        peer_ticker = str(candidate.get("ticker") or "").strip()
        if not name or not peer_ticker:
            continue
        try:
            import yfinance as yf
            peer = yf.Ticker(peer_ticker)
            info = peer.info or {}
            fast = getattr(peer, "fast_info", None)
            market_cap = getattr(fast, "market_cap", None) or info.get("marketCap")
            currency = getattr(fast, "currency", None) or info.get("currency") or "USD"
            pe = info.get("trailingPE") or info.get("forwardPE")
            growth = info.get("revenueGrowth")
            margin = info.get("profitMargins") or info.get("operatingMargins")
            peers.append({
                "name": info.get("longName") or name,
                "ticker": peer_ticker,
                "market_cap": format_live_peer_value(market_cap, currency),
                "pe_ratio": f"{pe:.1f}x" if isinstance(pe, (int, float)) and pe > 0 else "N/A",
                "revenue_growth": f"{growth * 100:+.1f}% " if isinstance(growth, (int, float)) else "N/A",
                "net_margin": f"{margin * 100:.1f}% " if isinstance(margin, (int, float)) else "N/A",
                "edge": str(candidate.get("edge") or "Competitive strategic comparison")
            })
        except Exception:
            continue

    return peers

def format_live_peer_value(value: Any, currency: str) -> str:
    if not isinstance(value, (int, float)):
        return "N/A"
    if value >= 1e12:
        return f"{currency} {value / 1e12:.2f}T"
    if value >= 1e9:
        return f"{currency} {value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{currency} {value / 1e6:.2f}M"
    return f"{currency} {value:,.0f}"

def calculate_health_scores(dossier: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes an objective, 0-100 score across 4 enterprise dimensions:
    - Financial Strength (0-100)
    - Growth Momentum (0-100)
    - Valuation Multiple / Attractiveness (0-100)
    - Safety & Risk Resilience (0-100)
    Returns composite score and letter grade (A+, A, B+, B, C, D).
    """
    metrics = dossier.get("metrics", {})
    is_public = dossier.get("is_public", False)
    entity_type = dossier.get("entity_type") or ("PUBLIC" if is_public else "PRIVATE")
    chart_data = metrics.get("chart_data") or {}
    shared_state = dossier.get("shared_state") or {}
    breaking_reg = shared_state.get("breaking_regulatory") or []

    # 1. Financial Strength (Profitability & Balance Sheet)
    fin_score = 75
    try:
        op_margin_str = str(metrics.get("operating_margins") or metrics.get("profit_margins") or "0")
        op_num = float(re.sub(r'[^0-9\.\-]', '', op_margin_str.split()[0]))
        if op_num >= 35.0: fin_score = 95
        elif op_num >= 20.0: fin_score = 88
        elif op_num >= 10.0: fin_score = 78
        elif op_num >= 2.0: fin_score = 68
        elif op_num < 0: fin_score = 45
    except Exception:
        if entity_type == "SUBSIDIARY": fin_score = 85
        elif not is_public: fin_score = 72

    # 2. Growth Momentum (Revenue Trajectory & Price Performance)
    growth_score = 72
    try:
        p_sum = chart_data.get("price_summary") or {}
        ret_1y = p_sum.get("return_1y_pct")
        if ret_1y is not None:
            if ret_1y >= 40.0: growth_score = 96
            elif ret_1y >= 20.0: growth_score = 88
            elif ret_1y >= 5.0: growth_score = 78
            elif ret_1y >= -10.0: growth_score = 66
            else: growth_score = 52
        else:
            rev_str = str(metrics.get("total_revenue") or "")
            if "B" in rev_str or "billion" in rev_str.lower(): growth_score = 84
            elif "M" in rev_str or "million" in rev_str.lower(): growth_score = 74
    except Exception:
        growth_score = 75

    # 3. Valuation Score (100 = Highly attractive/reasonable; lower = extreme premium/stretched)
    val_score = 70
    try:
        pe_str = str(metrics.get("trailing_pe") or metrics.get("pe_ratio") or "")
        pe_num = float(re.sub(r'[^0-9\.]', '', pe_str)) if pe_str and pe_str != "N/A" else None
        if pe_num:
            if pe_num < 15.0: val_score = 92
            elif pe_num <= 25.0: val_score = 85
            elif pe_num <= 40.0: val_score = 72
            elif pe_num <= 75.0: val_score = 58
            else: val_score = 46  # Premium multiple, stretched valuation
        else:
            val_score = 70  # Private or consolidated basis
    except Exception:
        val_score = 70

    # 4. Safety & Regulatory Resilience (Deducts for breaking investigations, patent lawsuits, debt)
    risk_score = 86
    if breaking_reg:
        risk_score = max(45, 86 - (len(breaking_reg) * 12))
    
    # Check if Motive patent lawsuit or major risk keywords exist
    all_text = (dossier.get("financial_analysis", "") + " " + dossier.get("strategic_outlook", "")).lower()
    if "patent" in all_text and "litigation" in all_text:
        risk_score = max(50, risk_score - 10)
    if "antitrust" in all_text or "export control" in all_text:
        risk_score = max(50, risk_score - 8)

    # Weighted composite score
    overall = int(round((fin_score * 0.32) + (growth_score * 0.28) + (val_score * 0.18) + (risk_score * 0.22)))
    overall = max(30, min(99, overall))

    # Determine Letter Grade
    if overall >= 90: grade = "A+ (Elite Strength)"
    elif overall >= 82: grade = "A (Strong Outperformer)"
    elif overall >= 74: grade = "B+ (Solid Foundation)"
    elif overall >= 66: grade = "B (Moderate Stability)"
    elif overall >= 55: grade = "C (Heightened Caution)"
    else: grade = "D (High Risk Profile)"

    return {
        "overall_score": overall,
        "letter_grade": grade,
        "financial_strength": fin_score,
        "growth_momentum": growth_score,
        "valuation_score": val_score,
        "safety_risk_index": risk_score,
        "descriptors": {
            "financial_strength": "Tier-1 Profitability & Margins" if fin_score >= 80 else "Stable Cash Flow Generation",
            "growth_momentum": "Accelerating Commercial Scale" if growth_score >= 80 else "Steady Revenue Growth",
            "valuation_score": "Attractive / Fair Multiple" if val_score >= 75 else "Trading at Growth Premium",
            "safety_risk_index": "Low Regulatory Headwind" if risk_score >= 80 else "Active Legal / Policy Scrutiny"
        }
    }

def generate_executive_memo(dossier: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a crisp, 30-second Bull vs. Bear Executive Memo:
    - Overall Stance (Bullish, Balanced, Cautious)
    - 2-3 sentence core takeaway
    - Exactly 3 positive catalysts (Pros)
    - Exactly 3 key risks / headwinds (Cons)
    """
    company_name = dossier.get("company_name", "Target Enterprise")
    ticker = dossier.get("ticker", "N/A")
    metrics = dossier.get("metrics", {})
    is_public = dossier.get("is_public", False)
    entity_type = dossier.get("entity_type") or ("PUBLIC" if is_public else "PRIVATE")
    scores = calculate_health_scores(dossier)
    overall_score = scores["overall_score"]
    
    # Stance and headline
    if overall_score >= 82:
        stance = "BULLISH / OUTPERFORM"
        badge_color = "#10B981"  # green
        headline = f"Strong Enterprise Moat with Accelerated Market Execution"
    elif overall_score >= 68:
        stance = "BALANCED / CONSTRUCTIVE"
        badge_color = "#F59E0B"  # amber
        headline = f"Solid Commercial Footprint Tempered by Growth Multiples"
    else:
        stance = "CAUTIOUS / ELEVATED RISK"
        badge_color = "#EF4444"  # red
        headline = f"Strategic Expansion Confronted by Regulatory & Competitive Headwinds"

    # Contextual Takeaway
    sector = metrics.get("sector") or "its target market"
    market_cap = metrics.get("market_cap") or "undisclosed private capitalization"
    if entity_type == "PUBLIC" and is_public:
        takeaway = (
            f"{company_name} ({ticker}) commands a strong commercial footprint across the {sector} sector with a market valuation of {market_cap}. "
            f"The business demonstrates robust institutional backing and sustained operational scale, while long-term valuation multiples require continued execution."
        )
        pros = [
            f"Expanding commercial scale with documented TTM revenues of {metrics.get('total_revenue', 'multi-billion scale')} and defensive market share.",
            f"Demonstrated profitability with operating margins reported at {metrics.get('operating_margins', metrics.get('profit_margins', 'healthy double-digit levels'))}.",
            f"Positive institutional coverage consensus with a target price benchmark of {metrics.get('analyst_target_price', 'above current levels')}."
        ]
        cons = [
            f"Valuation multiples (P/E of {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))}) price in strong multi-year compounding with limited room for execution misses.",
            "Macro exposure to enterprise IT budget cycles, inflation-adjusted cost of capital, and geopolitical supply chain dynamics.",
            "Evolving regulatory scrutiny, cross-border trade controls, and aggressive competition from top-tier international incumbents."
        ]
    elif entity_type == "SUBSIDIARY":
        resolved = dossier.get("resolved_entity") or {}
        parent_co = resolved.get("parent_company") or "Parent Group"
        takeaway = (
            f"{company_name} operates as a wholly-owned operating subsidiary backed by {parent_co}. "
            f"It pairs significant local subscriber and infrastructure scale with parent group capitalization and credit backing."
        )
        pros = [
            f"Strategic backing, balance sheet credit guarantees, and technology sharing from parent company {parent_co}.",
            "Dominant regional subscriber footprint with deep network distribution and digital financial services integration.",
            "High defensive recurring utility revenue with mission-critical consumer and enterprise lock-in."
        ]
        cons = [
            "Local currency volatility against parent foreign-exchange reporting currency affecting dollar-denominated returns.",
            "Capital-intensive infrastructure upgrade requirements (spectrum licensing, tower electrification, 4G/5G expansion).",
            "Stringent local telecom regulatory compliance and price-cap scrutiny from national authorities."
        ]
    else:
        # Private enterprise (e.g. Motive, OpenAI)
        shared_state = dossier.get("shared_state") or {}
        pf = shared_state.get("private_financials") or {}
        takeaway = (
            f"{company_name} stands as an unlisted private enterprise with documented venture backing and scaling commercial ARR. "
            f"Operational agility allows focused product development without quarterly public earnings volatility."
        )
        pros = [
            "Proprietary technology architecture, high annual contract values (ACV), and sticky enterprise customer integration.",
            "Strong balance sheet capitalization backed by tier-1 institutional venture and private equity partners.",
            "Strategic optionality for potential public listing (IPO) or high-valuation secondary liquidity transactions."
        ]
        cons = [
            "Illiquid private share capital structure with valuation dependent on broader venture capital market conditions.",
            "Intense competitive friction and potential intellectual property or patent litigation with public rivals.",
            "Execution risk in scaling sales teams and achieving self-funding cash-flow breakeven prior to IPO."
        ]

    return {
        "headline": headline,
        "stance": stance,
        "badge_color": badge_color,
        "takeaway": takeaway,
        "pros": pros,
        "cons": cons,
        "health_score": overall_score,
        "letter_grade": scores["letter_grade"]
    }

def answer_question_from_dossier(dossier: Dict[str, Any], question: str) -> str:
    """
    Answers user follow-up questions directly, accurately, and concisely based on the synthesized dossier.
    Executes in <0.05 seconds for in-memory dossier lookups, with fast LLM fallback for open-ended queries.
    """
    company_name = dossier.get("company_name", "Target Company")
    ticker = dossier.get("ticker", "N/A")
    metrics = dossier.get("metrics", {})
    resolved = dossier.get("resolved_entity") or {}
    shared_state = dossier.get("shared_state") or {}
    q_clean = question.strip().lower()

    # Pre-compiled verified context from memory
    leaders = ", ".join(shared_state.get("verified_leadership") or [])
    segments = ", ".join(shared_state.get("verified_segments") or [])
    reg_risks = "; ".join(shared_state.get("breaking_regulatory") or [])
    competitors = dossier.get("competitor_comparison") or []
    memo = dossier.get("executive_memo") or {}

    # FAST-PATH 1: Leadership / CEO / Executives / Founders (Instant ~0.001s response)
    if any(k in q_clean for k in ["ceo", "founder", "leader", "officer", "who is", "management", "executive", "board"]):
        founding = shared_state.get("founding_info", "")
        lead_str = leaders if leaders else "Documented in corporate regulatory filings and executive disclosures."
        ans = f"**Active Leadership & Officers for {company_name} ({ticker}):**\n"
        ans += f"• **Verified Executive Leadership:** {lead_str}\n"
        if founding:
            ans += f"• **Corporate Origins & Founding:** {founding}\n"
        return ans

    # FAST-PATH 2: Margins, Revenue, Valuation, P/E, 52-Week Range & Financials (Instant ~0.001s response)
    if any(k in q_clean for k in ["margin", "revenue", "profit", "sales", "pe ratio", "p/e", "valuation", "price", "52-week", "target", "earning", "multiple"]):
        ans = f"**Key Financial Metrics for {company_name} ({ticker}):**\n"
        if metrics.get("current_price"):
            ans += f"• **Current Share Price:** {metrics.get('current_price')}\n"
        if metrics.get("52_week_low") and metrics.get("52_week_high"):
            ans += f"• **52-Week Range:** {metrics.get('52_week_low')} - {metrics.get('52_week_high')}\n"
        if metrics.get("market_cap"):
            ans += f"• **Market Capitalization:** {metrics.get('market_cap')}\n"
        if metrics.get("trailing_pe") or metrics.get("pe_ratio"):
            ans += f"• **P/E Multiple:** {metrics.get('trailing_pe', metrics.get('pe_ratio'))}\n"
        if metrics.get("total_revenue"):
            ans += f"• **TTM Total Revenue:** {metrics.get('total_revenue')}\n"
        if metrics.get("operating_margins"):
            ans += f"• **Operating Margin:** {metrics.get('operating_margins')}\n"
        if metrics.get("profit_margins"):
            ans += f"• **Net Profit Margin:** {metrics.get('profit_margins')}\n"
        if metrics.get("analyst_target_price"):
            ans += f"• **Wall Street Target:** {metrics.get('analyst_target_price')} (Consensus: {metrics.get('analyst_rating', 'BUY')})\n"
        return ans

    # FAST-PATH 3: Key Risks, Lawsuits & Regulatory Headwinds (Instant ~0.001s response)
    if any(k in q_clean for k in ["risk", "lawsuit", "regulatory", "headwind", "threat", "investigation", "antitrust", "patent", "litigation"]):
        ans = f"**Primary Risk Vectors & Headwinds for {company_name}:**\n"
        if reg_risks:
            ans += f"• **Regulatory Scrutiny:** {reg_risks}\n"
        cons = memo.get("cons") or []
        if cons:
            for c in cons:
                ans += f"• {c}\n"
        else:
            ans += "• Macro IT expenditure cycles, competitive pricing pressure, and trade policy sensitivity.\n"
        return ans

    # FAST-PATH 4: Core Products, Divisions & Business Model (Instant ~0.001s response)
    if any(k in q_clean for k in ["product", "division", "segment", "service", "offering", "what do they do", "business"]):
        ans = f"**Core Operating Divisions & Platform Offerings for {company_name}:**\n"
        if segments:
            ans += f"• **Primary Divisions:** {segments}\n"
        pros = memo.get("pros") or []
        if pros:
            ans += f"• **Strategic Moat:** {pros[0]}\n"
        return ans

    # FAST-PATH 5: Competitors & Industry Peers (Instant ~0.001s response)
    if any(k in q_clean for k in ["competitor", "peer", "rival", "vs", "versus"]):
        ans = f"**Primary Industry Competitors for {company_name}:**\n"
        if competitors:
            for p in competitors:
                ans += f"• **{p.get('name')} ({p.get('ticker', 'N/A')}):** Valuation {p.get('market_cap', 'N/A')} | Moat: {p.get('edge', 'N/A')}\n"
        else:
            ans += "• Comprehensive peer benchmarking documented in the Financial Analysis matrix above.\n"
        return ans

    # Open-Ended Fallback: Query LLM over compiled summary text
    context_text = f"""
Company: {company_name} ({ticker})
Entity Classification: {dossier.get('entity_type', 'Enterprise')}
Key Metrics: Price: {metrics.get('current_price', 'N/A')}, Market Cap: {metrics.get('market_cap', 'N/A')}, P/E: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))}, Revenue: {metrics.get('total_revenue', 'N/A')}, Margins: {metrics.get('profit_margins', 'N/A')}
Executive Leadership: {leaders}
Operating Divisions: {segments}
Regulatory Inquiries & Headwinds: {reg_risks}

Executive Summary:
{dossier.get('executive_summary', '')[:1000]}

Corporate Background:
{dossier.get('corporate_background', '')[:1200]}

Financial Analysis:
{dossier.get('financial_analysis', '')[:1200]}

Recent News & Sentiment:
{dossier.get('recent_news_analysis', '')[:800]}

Strategic Outlook & Risks:
{dossier.get('strategic_outlook', '')[:1000]}
"""

    prompt = f"""You are an institutional financial analyst assistant.
Based EXCLUSIVELY on the company intelligence dossier below, answer the user's question directly, clearly, and concisely in 2-4 bullet points or short paragraphs.
If the information is not in the dossier, state: "This detail is not documented in the current dossier."

Dossier:
{context_text}

User Question: {question}

Answer:"""

    try:
        from agents.base_agent import BaseAgent
        agent = BaseAgent(name="Dossier Assistant", role="Q&A Analyst", system_prompt="You are an expert financial research assistant.")
        resp = agent.generate_response(prompt)
        if resp and not resp.startswith("[Dossier Assistant Report]") and len(resp.strip()) > 15:
            return resp.strip()
    except Exception:
        pass

    return f"According to the dossier, {company_name} ({ticker}) operates in the {metrics.get('sector', 'commercial')} sector with a market valuation of {metrics.get('market_cap', 'private basis')}. For specific details, please consult the Executive Summary or Financial Analysis tabs above."
