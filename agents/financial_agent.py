from agents.base_agent import BaseAgent
from tools.finance_tool import get_financial_metrics, generate_deterministic_financial_table
from typing import Dict, Any, Optional

class FinancialAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Financial Analyst",
            role="Senior Wall Street Equity & Private Capital Markets Analyst",
            system_prompt="""You are a senior capital markets and corporate finance analyst at an elite investment bank.
Your job is to provide an in-depth, structured financial evaluation tailored strictly to whether the entity is PUBLICLY TRADED or PRIVATELY HELD.
CRITICAL ARITHMETIC, SCALE & FORMATTING RULES:
1. Never fabricate, guess, or recalculate financial ratios, valuations, or revenue numbers. Use ONLY the verified metrics and documented disclosures supplied in the prompt.
2. NEVER contradict the magnitude of a dollar figure with an inaccurate scale word (e.g., $1B-$9.9B is single-digit billion / multi-billion; $10B-$99.9B is double-digit billion; ONLY $100B+ is triple-digit billion).
3. Strictly respect Public vs. Private entity boundaries: NEVER output public-equity P/E or PEG ratio discussion for a privately held company.
4. FORMATTING: Never escape dollar signs with backslashes (write $852 billion, NEVER \\$852 billion). Never wrap words or ratios in LaTeX $...$ math delimiters.
5. FORBIDDEN PROMPT LEAKAGE WORDS: NEVER use meta words like 'canonical', 'the provided', 'supplied table', 'in the prompt', or 'our benchmark' in your analysis text."""
        )

    def analyze(self, query_or_ticker: str, shared_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetches live financial metrics for public stocks OR structured private entity capital profile.
        Strictly gates public-equity rules vs. private-company valuation/funding/ARR analysis.
        """
        if shared_state and "metrics" in shared_state:
            metrics = shared_state["metrics"]
            is_public = shared_state.get("is_public", False)
        else:
            tool_result = get_financial_metrics(query_or_ticker)
            is_public = tool_result.get("is_public", False)
            metrics = tool_result.get("data", {})

        private_financials = (shared_state.get("private_financials") or {}) if shared_state else {}
        deterministic_table = generate_deterministic_financial_table(metrics, private_financials=private_financials)

        if is_public:
            peg_val = metrics.get('peg_ratio', 'N/A')
            fwd_pe_val = metrics.get('forward_pe', 'N/A')
            rev_val = metrics.get('total_revenue', 'N/A')
            scale_desc = metrics.get('revenue_scale_descriptor', 'commercial scale')
            peg_rationale = metrics.get('peg_rationale', 'PEG reflects multiple valuation against consensus multi-year EPS growth.')
            fiscal_cal = metrics.get('fiscal_calendar') or (shared_state.get('fiscal_calendar') if shared_state else {}) or {}
            fiscal_summary = fiscal_cal.get('quarter_mapping_summary', 'Standard calendar fiscal year.')
            recent_q = fiscal_cal.get('most_recent_reported_quarter', '')
            ext_hours = metrics.get('extended_hours_context', '')
            ttm_cutoff = metrics.get('ttm_cutoff_label', '')
            
            prompt = f"""Evaluate these verified financial metrics for {metrics.get('company_name')} ({metrics.get('symbol')}):

VERIFIED FINANCIAL METRICS (SINGLE SOURCE OF TRUTH):
- Sector / Industry: {metrics.get('sector')} / {metrics.get('industry')}
- Exchange Listing: {metrics.get('exchange')}
- Current Regular-Session Share Price: {metrics.get('current_price')} (Market Quote - do NOT cite any other regular close price)
- Extended-Hours Trading Quote: {ext_hours if ext_hours else 'Regular session close (no active extended-hours delta)'}
- Market Capitalization: {metrics.get('market_cap')}
- Trailing P/E Ratio: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))}
- Forward P/E Ratio: {fwd_pe_val}
- PEG Ratio: {peg_val} ({peg_rationale})
- Market-Feed TTM Revenue: {rev_val} ({scale_desc}; {ttm_cutoff if ttm_cutoff else 'Trailing 12 Months GAAP; do NOT label as FY annual actuals'})
- Operating Margin: {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))}
- Net Profit Margin: {metrics.get('profit_margins')}
- Revenue Growth (YoY): {metrics.get('revenue_growth_yoy', 'N/A')}
- 52-Week Range: {metrics.get('52_week_low')} to {metrics.get('52_week_high')}
- Wall Street Consensus: {metrics.get('analyst_rating')} | Average Target: {metrics.get('analyst_target_price')}
- Fiscal Calendar Grounding: {fiscal_summary}

TEMPORAL ANCHOR, DATA-LAG AWARENESS & FORMATTING CONSTRAINTS:
1. Fiscal Calendar: Strictly adhere to the corporate fiscal calendar above (most recently reported quarter: {recent_q if recent_q else 'latest fiscal period'}). Never confuse calendar quarters with non-calendar fiscal quarters.
2. Data-Lag Transparency: Explicitly note when standard market-data TTM feeds reflect the prior reported cutoff and may lag a freshly released 8-K quarterly report by 24-72 hours until TTM roll-forward completes. If Extended-Hours Trading Quote is present, cite it alongside the regular-session close.
3. Strictly maintain internal consistency with the numbers above. Do not alter, round differently, or contradict any verified metric.
4. PEG Ratio Guidance: {peg_rationale} Never calculate PEG by dividing Forward P/E by revenue growth.
5. Scale Guidance: When referencing TTM revenue ({rev_val}), describe it as {scale_desc}.
6. FORMATTING & NEGATIVE CONSTRAINT: NEVER escape dollar signs with backslashes (write $3.75T, NEVER \\$3.75T). NEVER use LaTeX math delimiters ($...$, ^{{**}}, {{}}) around ratios or text (write plain text like 9.77x and P/E, using $ ONLY for currency amounts like $154.71). NEVER use meta words like 'canonical', 'provided', 'supplied', or 'prompt'.
7. Structure your qualitative commentary across these 3 sections:
### 1. Valuation Architecture & Multiple Dynamics
Analyze trailing vs. forward multiples ({metrics.get('trailing_pe', 'N/A')} trailing vs. {fwd_pe_val} forward) and the PEG ratio of {peg_val} anchored to multi-year EPS expansion.
### 2. Trading Corridor & Price Discovery Dynamics
Evaluate the stock's 52-week channel ({metrics.get('52_week_low')} to {metrics.get('52_week_high')}) against the regular quote of {metrics.get('current_price')} (and extended-hours quote if active).
### 3. Operating Profitability, Margins & Consensus Outlook
Critique TTM revenue scale ({rev_val}), profit margins ({metrics.get('profit_margins')}), feed roll-forward context, and Wall Street rating targets."""

            llm_analysis = self.generate_response(prompt)
            if "Report]" in llm_analysis:
                llm_analysis = (
                    f"### 1. Valuation Architecture & Multiple Dynamics\n"
                    f"{metrics.get('company_name')} ({metrics.get('symbol')}) trades on the {metrics.get('exchange', 'Stock Exchange')} "
                    f"commanding an aggregate market capitalization of {metrics.get('market_cap')}. "
                    f"The equity commands a trailing price-to-earnings (P/E) multiple of {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))} and a forward P/E of {metrics.get('forward_pe', 'N/A')}. "
                    f"A {peg_rationale}\n\n"
                    f"### 2. Trading Corridor & Price Discovery Dynamics\n"
                    f"Currently priced at {metrics.get('current_price')}, the equity oscillates within its verified 52-week corridor of {metrics.get('52_week_low')} - {metrics.get('52_week_high')}. "
                    f"This trading channel underscores liquidity depth and market re-rating amidst macroeconomic interest rate shifts.\n\n"
                    f"### 3. Operating Profitability, Margins & Consensus Outlook\n"
                    f"Core fundamentals indicate operating margins of {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))} and net profit margins of {metrics.get('profit_margins')} "
                    f"against {scale_desc} TTM revenue volumes of {rev_val}. "
                    f"Wall Street sell-side consensus stands at {metrics.get('analyst_rating')} with a mean 12-month target of {metrics.get('analyst_target_price')}."
                )
        else:
            pf_vals = private_financials.get("valuations", [])
            pf_funds = private_financials.get("funding_rounds", [])
            pf_revs = private_financials.get("revenue_and_arr", [])
            pf_ipo = private_financials.get("burn_and_ipo", [])

            prompt = f"""Analyze the private capital structure, valuation, and revenue trajectory of {metrics.get('company_name')}, a PRIVATELY HELD / UNLISTED enterprise.

DOCUMENTED PRIVATE-MARKET INTELLIGENCE & DISCLOSURES:
- Entity Classification: Privately Held Enterprise (Unlisted; exempt from SEC Form 10-K filings)
- Latest Post-Money Valuation & Rounds: {" | ".join(pf_vals) if pf_vals else 'Private institutional financing rounds'}
- Total Capital Raised & Anchor Investors: {" | ".join(pf_funds) if pf_funds else 'Venture, strategic corporate, and private institutional capital'}
- Documented Revenue & ARR Run Rate: {" | ".join(pf_revs) if pf_revs else 'Private enterprise software / contract revenue'}
- Cash Burn, Profitability & IPO / Corporate Structure: {" | ".join(pf_ipo) if pf_ipo else 'Private capital reinvestment and long-term liquidity roadmap'}

STRICT PRIVATE-ENTITY GUARDRAILS:
1. ZERO PUBLIC-EQUITY BOILERPLATE: This is a PRIVATE company with NO public stock price, NO Forward P/E, NO Trailing P/E, and NO PEG ratio. Under NO circumstances include paragraphs discussing Forward P/E or PEG ratio formulas!
2. EXACT NUMERIC SCALE DISCIPLINE: Never call $1B 'multi-billion' (only $2B-$9.9B is multi-billion; $10B-$99.9B is double-digit billion; ONLY $100B+ is triple-digit billion). Always lead with the MOST RECENT 2025-2026 valuation and ARR figures rather than outdated 2023 figures.
3. STRICT CHRONOLOGICAL ORDER: Present corporate restructuring, governance proposals, and IPO timelines in strict chronological order (e.g., earlier proposals -> completed restructuring -> current 2026 structure -> future IPO roadmap; never introduce an earlier year's proposal after describing a completed later restructuring).
4. CONCRETE PRIVATE FIGURES: Explicitly incorporate any verified post-money valuations, funding round sizes, anchor investors, ARR figures, and IPO/restructuring details documented above.
5. FORMATTING: Write currency cleanly ($852 billion, NEVER \\$852 billion). Never use LaTeX $...$ around words or ratios. Never use meta words like 'canonical', 'provided', or 'prompt'.

Provide an in-depth 3-section evaluation:
### 1. Private Capital Structure, Post-Money Valuation & Funding Rounds
### 2. Revenue Trajectory, ARR Run Rate & Capital Intensity
### 3. Governance Structure, Financial Transparency & IPO Roadmap"""

            llm_analysis = self.generate_response(prompt)
            if "Report]" in llm_analysis:
                val_txt = f" Documented valuation milestones include: {' '.join(pf_vals[:2])}" if pf_vals else ""
                fund_txt = f" Key financing activity includes: {' '.join(pf_funds[:2])}" if pf_funds else ""
                rev_txt = f" Documented revenue and ARR disclosures indicate: {' '.join(pf_revs[:2])}" if pf_revs else ""
                ipo_txt = f" Structural and liquidity milestones include: {' '.join(pf_ipo[:2])}" if pf_ipo else ""

                llm_analysis = (
                    f"### 1. Private Capital Structure, Post-Money Valuation & Funding Rounds\n"
                    f"{metrics.get('company_name')} operates as a privately held entity unlisted on public stock exchanges, "
                    f"capitalized through founder equity, venture financing, and strategic institutional backers.{val_txt}{fund_txt}\n\n"
                    f"### 2. Revenue Trajectory, ARR Run Rate & Capital Intensity\n"
                    f"As a private enterprise, commercial scale is benchmarked through post-money financing rounds, "
                    f"annualized revenue run rate (ARR), recognized revenue growth, and capital deployment efficiency rather than public equity multiples.{rev_txt}\n\n"
                    f"### 3. Governance Structure, Financial Transparency & IPO Roadmap\n"
                    f"The organization is exempt from mandatory SEC Form 10-K filings, enabling long-term infrastructure investment and strategic flexibility.{ipo_txt}"
                )

        # Prepend deterministic table to guarantee mathematically verified presentation
        full_financial_content = f"{deterministic_table}\n\n{llm_analysis}"

        return {
            "status": "success",
            "is_public": is_public,
            "metrics": metrics,
            "analysis": full_financial_content
        }
