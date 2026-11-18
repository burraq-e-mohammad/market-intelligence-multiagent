from agents.base_agent import BaseAgent
from tools.finance_tool import get_financial_metrics, generate_deterministic_financial_table
from typing import Dict, Any, Optional

class FinancialAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Financial Analyst",
            role="Senior Wall Street Equity & Capital Markets Analyst",
            system_prompt="""You are a senior equity research and capital markets analyst at an elite Wall Street investment bank.
Your job is to provide an in-depth, structured financial evaluation. Do NOT write a short summary.
You MUST adhere strictly to the Single Source of Truth provided in the prompt.
CRITICAL ARITHMETIC & FACTUAL RULES:
1. Never fabricate, guess, or recalculate financial ratios, share prices, or market caps. Use ONLY the verified metrics provided.
2. The provided revenue figure is strictly Trailing Twelve Months (TTM) GAAP revenue. Accurately characterize revenue volume according to its verified scale descriptor (e.g. trillion-dollar, triple-digit billion, or multi-billion scale; never describe a hundred-billion scale as 'double-digit scale').
3. PEG Ratio Calculation: The PEG ratio is mathematically defined as Forward P/E divided by consensus long-term expected EPS compound growth, NOT revenue growth. Under NO circumstances divide Forward P/E by revenue growth to reverse-engineer the PEG.
4. FORBIDDEN PROMPT LEAKAGE WORDS: NEVER use meta words like 'canonical', 'the provided', 'supplied table', 'in the prompt', or 'our benchmark' in your analysis text. Write exclusively in the independent, professional voice of an institutional managing director.
5. Do NOT invent forward dollar projections or build tables with unverified segment numbers that do not sum to the verified total."""
        )

    def analyze(self, query_or_ticker: str, shared_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetches live financial metrics for public stocks OR structured private entity profile.
        Incorporates canonical shared state and embeds deterministic tables.
        """
        if shared_state and "metrics" in shared_state:
            metrics = shared_state["metrics"]
            is_public = shared_state.get("is_public", False)
        else:
            tool_result = get_financial_metrics(query_or_ticker)
            is_public = tool_result.get("is_public", False)
            metrics = tool_result.get("data", {})
        
        deterministic_table = generate_deterministic_financial_table(metrics)

        if is_public:
            peg_val = metrics.get('peg_ratio', 'N/A')
            fwd_pe_val = metrics.get('forward_pe', 'N/A')
            rev_val = metrics.get('total_revenue', 'N/A')
            scale_desc = metrics.get('revenue_scale_descriptor', 'commercial scale')
            peg_rationale = metrics.get('peg_rationale', 'PEG reflects multiple valuation against consensus multi-year EPS growth.')
            fiscal_cal = metrics.get('fiscal_calendar') or (shared_state.get('fiscal_calendar') if shared_state else {}) or {}
            fiscal_summary = fiscal_cal.get('quarter_mapping_summary', 'Standard calendar fiscal year.')
            recent_q = fiscal_cal.get('most_recent_reported_quarter', '')
            
            prompt = f"""Evaluate these verified financial metrics for {metrics.get('company_name')} ({metrics.get('symbol')}):

VERIFIED FINANCIAL METRICS (SINGLE SOURCE OF TRUTH):
- Sector / Industry: {metrics.get('sector')} / {metrics.get('industry')}
- Exchange Listing: {metrics.get('exchange')}
- Current Share Price: {metrics.get('current_price')} (Market Quote - do NOT cite any other price)
- Market Capitalization: {metrics.get('market_cap')}
- Trailing P/E Ratio: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))}
- Forward P/E Ratio: {fwd_pe_val}
- PEG Ratio: {peg_val} ({peg_rationale})
- TTM Revenue (Trailing 12 Months): {rev_val} ({scale_desc}; do NOT label as FY annual actuals)
- Operating Margin: {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))}
- Net Profit Margin: {metrics.get('profit_margins')}
- Revenue Growth (YoY): {metrics.get('revenue_growth_yoy', 'N/A')}
- 52-Week Range: {metrics.get('52_week_low')} to {metrics.get('52_week_high')}
- Wall Street Consensus: {metrics.get('analyst_rating')} | Average Target: {metrics.get('analyst_target_price')}
- Fiscal Calendar Grounding: {fiscal_summary}

TEMPORAL ANCHOR, FISCAL CALENDAR & FORMATTING CONSTRAINTS:
1. Fiscal Calendar: Strictly adhere to the corporate fiscal calendar above (most recently reported quarter: {recent_q if recent_q else 'latest fiscal period'}). Never confuse calendar quarters with non-calendar fiscal quarters.
2. Strictly maintain internal consistency with the numbers above. Do not alter, round differently, or contradict any verified metric.
3. PEG Ratio Guidance: {peg_rationale} Never calculate PEG by dividing Forward P/E by revenue growth.
4. Scale Guidance: When referencing TTM revenue ({rev_val}), describe it as {scale_desc}.
5. FORMATTING & NEGATIVE CONSTRAINT: NEVER use LaTeX math delimiters ($...$, ^{{**}}, {{}}) around ratios or text (write plain text like 9.77x and P/E, using $ ONLY for currency amounts like $154.71). NEVER use meta words like 'canonical', 'provided', 'supplied', or 'prompt'.
6. Structure your qualitative commentary across these 3 sections:
### 1. Valuation Architecture & Multiple Dynamics
Analyze trailing vs. forward multiples ({metrics.get('trailing_pe', 'N/A')} trailing vs. {fwd_pe_val} forward) and the PEG ratio of {peg_val} anchored to multi-year EPS expansion.
### 2. Trading Corridor & Price Discovery Dynamics
Evaluate the stock's 52-week channel ({metrics.get('52_week_low')} to {metrics.get('52_week_high')}) against the current quote of {metrics.get('current_price')}.
### 3. Operating Profitability, Margins & Consensus Outlook
Critique TTM revenue scale ({rev_val}), profit margins ({metrics.get('profit_margins')}), and Wall Street rating targets."""

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
            prompt = f"""Analyze the financial structure of {metrics.get('company_name')}, a PRIVATELY HELD enterprise.
Note that it is unlisted on public stock exchanges, exempt from public SEC filings, and relies on venture funding, private equity, or operational cash flows.
Provide an in-depth 3-section evaluation:
### 1. Corporate Classification & Private Capital Structure
### 2. Private Valuation Mechanics & Growth Metrics
### 3. Financial Transparency, Governance & Capital Access"""

            llm_analysis = self.generate_response(prompt)
            if "Report]" in llm_analysis:
                llm_analysis = (
                    f"### 1. Corporate Classification & Private Capital Structure\n"
                    f"{metrics.get('company_name')} operates as a privately held entity unlisted on major public exchanges. "
                    f"The capital structure is anchored by founder equity, venture funding, or strategic private investors.\n\n"
                    f"### 2. Private Valuation Mechanics & Growth Metrics\n"
                    f"Unlike public stocks, enterprise valuation is evaluated through private financing rounds, revenue multiples, "
                    f"and annual recurring contract values rather than daily secondary market trades.\n\n"
                    f"### 3. Financial Transparency, Governance & Capital Access\n"
                    f"The enterprise is exempt from mandatory SEC 10-K disclosures, preserving operational flexibility and long-term strategic focus."
                )

        # Prepend deterministic table to guarantee mathematically verified presentation
        full_financial_content = f"{deterministic_table}\n\n{llm_analysis}"

        return {
            "status": "success",
            "is_public": is_public,
            "metrics": metrics,
            "analysis": full_financial_content
        }
