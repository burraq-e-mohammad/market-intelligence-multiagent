from agents.base_agent import BaseAgent
from tools.finance_tool import get_financial_metrics
from typing import Dict, Any

class FinancialAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Financial Analyst",
            role="Senior Wall Street Equity & Capital Markets Analyst",
            system_prompt="""You are a senior equity research and capital markets analyst at a major investment bank.
Your job is to provide an in-depth, structured financial evaluation. Do NOT write a short 2-line summary.
Provide detailed analysis across 3 distinct sections:
### 1. Valuation Architecture & Market Capitalization
Evaluate market cap, P/E multiples, and how the current valuation compares to growth expectations.
### 2. Trading Dynamics & 52-Week Price Channel
Analyze trading range, support/resistance context, and volatility patterns.
### 3. Operating Profitability, Revenue & Analyst Consensus
Evaluate margins, revenue magnitude, and Wall Street rating targets."""
        )

    def analyze(self, query_or_ticker: str) -> Dict[str, Any]:
        """
        Fetches live financial metrics for public stocks OR structured private entity profile.
        """
        tool_result = get_financial_metrics(query_or_ticker)
        is_public = tool_result.get("is_public", False)
        metrics = tool_result.get("data", {})
        
        if is_public:
            prompt = f"""Evaluate these public financial metrics for {metrics.get('company_name')} ({metrics.get('symbol')}):
- Sector / Industry: {metrics.get('sector')} / {metrics.get('industry')}
- Exchange: {metrics.get('exchange')}
- Current Stock Price: {metrics.get('current_price')}
- Market Capitalization: {metrics.get('market_cap')}
- P/E Multiple: {metrics.get('pe_ratio')}
- 52-Week Trading Range: {metrics.get('52_week_low')} to {metrics.get('52_week_high')}
- Total Revenue: {metrics.get('total_revenue')}
- Profit Margins: {metrics.get('profit_margins')}
- Consensus Rating: {metrics.get('analyst_rating')}
- Price Target: {metrics.get('analyst_target_price')}

Structure your response into 3 detailed sections:
### 1. Valuation Architecture & Market Capitalization
### 2. Trading Dynamics & 52-Week Price Channel
### 3. Operating Profitability, Revenue & Analyst Consensus

Write an in-depth, data-backed financial critique."""

            llm_analysis = self.generate_response(prompt)
            if "Report]" in llm_analysis:
                llm_analysis = (
                    f"### 1. Valuation Architecture & Market Capitalization\n"
                    f"{metrics.get('company_name')} ({metrics.get('symbol')}) trades on the {metrics.get('exchange', 'Stock Exchange')} "
                    f"commanding an aggregate market capitalization of {metrics.get('market_cap')}. "
                    f"The equity commands a price-to-earnings (P/E) multiple of {metrics.get('pe_ratio')}, reflecting investor expectations around cash flow stability.\n\n"
                    f"### 2. Trading Dynamics & 52-Week Price Channel\n"
                    f"Currently priced at {metrics.get('current_price')}, the stock fluctuates within its established 52-week corridor of {metrics.get('52_week_low')} - {metrics.get('52_week_high')}. "
                    f"This channel underscores trading liquidity and reflects historical price consolidation across recent market cycles.\n\n"
                    f"### 3. Operating Profitability, Revenue & Analyst Consensus\n"
                    f"Financial fundamentals indicate operating margins of {metrics.get('profit_margins')} against total revenue volume of {metrics.get('total_revenue')}. "
                    f"Analyst consensus stands at {metrics.get('analyst_rating')} with an average target price projection of {metrics.get('analyst_target_price')}."
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

        return {
            "status": "success",
            "is_public": is_public,
            "metrics": metrics,
            "analysis": llm_analysis
        }
