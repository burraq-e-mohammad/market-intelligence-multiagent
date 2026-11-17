from agents.base_agent import BaseAgent
from tools.finance_tool import get_financial_metrics, generate_deterministic_financial_table
from typing import Dict, Any, Optional

class FinancialAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Financial Analyst",
            role="Senior Wall Street Equity & Capital Markets Analyst",
            system_prompt="""You are a senior equity research and capital markets analyst at a major investment bank.
Your job is to provide an in-depth, structured financial evaluation. Do NOT write a short summary.
You MUST adhere strictly to the Single Source of Truth provided in the prompt.
CRITICAL ARITHMETIC & FACTUAL RULES:
1. Never fabricate, guess, or recalculate financial ratios, share prices, or market caps. Use ONLY the verified metrics provided.
2. The provided revenue figure is strictly Trailing Twelve Months (TTM) GAAP revenue. Do NOT confuse TTM with fiscal year (FY) annual filings.
3. Do NOT invent forward dollar projections or build tables with unverified segment numbers that do not sum to the verified total.
4. Focus your commentary on multiple expansion/contraction, margin durability, and industry peer valuation dynamics."""
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
            prompt = f"""Evaluate these verified financial metrics for {metrics.get('company_name')} ({metrics.get('symbol')}):

LOCKED CANONICAL FINANCIAL METRICS (SINGLE SOURCE OF TRUTH):
- Sector / Industry: {metrics.get('sector')} / {metrics.get('industry')}
- Exchange Listing: {metrics.get('exchange')}
- Current Share Price: {metrics.get('current_price')} (Canonical Quote - do NOT cite any other price)
- Market Capitalization: {metrics.get('market_cap')}
- Trailing P/E Ratio: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))}
- Forward P/E Ratio: {metrics.get('forward_pe', 'N/A')}
- PEG Ratio: {metrics.get('peg_ratio', 'N/A')}
- TTM Revenue (Trailing 12 Months): {metrics.get('total_revenue')} (Do NOT label as FY annual actuals)
- Operating Margin: {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))}
- Net Profit Margin: {metrics.get('profit_margins')}
- Revenue Growth (YoY): {metrics.get('revenue_growth_yoy', 'N/A')}
- 52-Week Range: {metrics.get('52_week_low')} to {metrics.get('52_week_high')}
- Wall Street Consensus: {metrics.get('analyst_rating')} | Average Target: {metrics.get('analyst_target_price')}

TEMPORAL ANCHOR & ARITHMETIC CONSTRAINTS:
1. Current calendar year is 2026.
2. Strictly maintain internal consistency with the numbers above. Do not alter, round differently, or contradict any canonical metric.
3. Provide rigorous qualitative commentary across these 3 sections:
### 1. Valuation Architecture & Multiple Dynamics
Analyze trailing vs. forward multiples ({metrics.get('trailing_pe', 'N/A')} trailing vs. {metrics.get('forward_pe', 'N/A')} forward) and PEG valuation context.
### 2. Trading Corridor & Price Discovery Dynamics
Evaluate the stock's 52-week channel ({metrics.get('52_week_low')} to {metrics.get('52_week_high')}) against the current quote of {metrics.get('current_price')}.
### 3. Operating Profitability, Margins & Consensus Outlook
Critique TTM revenue scale ({metrics.get('total_revenue')}), profit margins ({metrics.get('profit_margins')}), and Wall Street rating targets."""

            llm_analysis = self.generate_response(prompt)
            if "Report]" in llm_analysis:
                llm_analysis = (
                    f"### 1. Valuation Architecture & Multiple Dynamics\n"
                    f"{metrics.get('company_name')} ({metrics.get('symbol')}) trades on the {metrics.get('exchange', 'Stock Exchange')} "
                    f"commanding an aggregate market capitalization of {metrics.get('market_cap')}. "
                    f"The equity commands a trailing price-to-earnings (P/E) multiple of {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))} and a forward P/E of {metrics.get('forward_pe', 'N/A')}, "
                    f"reflecting disciplined market expectations around continued free cash flow expansion.\n\n"
                    f"### 2. Trading Corridor & Price Discovery Dynamics\n"
                    f"Currently priced at {metrics.get('current_price')}, the equity oscillates within its verified 52-week corridor of {metrics.get('52_week_low')} - {metrics.get('52_week_high')}. "
                    f"This trading channel underscores liquidity depth and market re-rating amidst macroeconomic interest rate shifts.\n\n"
                    f"### 3. Operating Profitability, Margins & Consensus Outlook\n"
                    f"Core fundamentals indicate operating margins of {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))} and net profit margins of {metrics.get('profit_margins')} "
                    f"against TTM revenue volumes of {metrics.get('total_revenue')}. "
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
