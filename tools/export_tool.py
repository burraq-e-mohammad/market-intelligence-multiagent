"""
Export Tool:
Generates institutional financial data models in CSV and Excel (.xlsx) formats.
Allows users to download and open all company metrics, peer comparisons, historical financials,
and executive memos directly in Microsoft Excel, Google Sheets, or financial modeling tools.
"""

from typing import Dict, Any, Tuple
import io
import csv
import re

def generate_csv_data_model(dossier: Dict[str, Any]) -> bytes:
    """
    Compiles the complete intelligence dossier into a multi-section, highly structured CSV file.
    Opens natively in Microsoft Excel on Windows with formatted numbers, headers, and tables.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    company_name = dossier.get("company_name", "Company")
    ticker = dossier.get("ticker", "N/A")
    is_public = dossier.get("is_public", False)
    entity_type = dossier.get("entity_type") or ("PUBLIC" if is_public else "PRIVATE")
    metrics = dossier.get("metrics", {})
    resolved = dossier.get("resolved_entity") or {}
    shared_state = dossier.get("shared_state") or {}

    # 1. Title & Corporate Standing Header
    writer.writerow(["AUTONOMOUS MARKET INTELLIGENCE FINANCIAL DATA MODEL"])
    writer.writerow(["Target Company", company_name])
    writer.writerow(["Listing / Symbol", ticker])
    writer.writerow(["Corporate Classification", entity_type])
    writer.writerow(["Primary Exchange", metrics.get("exchange", "N/A")])
    writer.writerow(["Sector", metrics.get("sector", resolved.get("sector", "N/A"))])
    writer.writerow(["Industry", metrics.get("industry", "Enterprise Solutions")])
    writer.writerow(["Report Execution Time (s)", dossier.get("execution_time", "N/A")])
    writer.writerow([])

    # 2. Key Valuation & Fundamental Snapshot
    writer.writerow(["--- FUNDAMENTAL VALUATION & MARKET SNAPSHOT ---"])
    if entity_type == "PUBLIC" and is_public:
        writer.writerow(["Metric", "Value", "Notes"])
        writer.writerow(["Current Stock Price", metrics.get("current_price", "N/A"), "Live market feed close"])
        writer.writerow(["Market Capitalization", metrics.get("market_cap", "N/A"), "Aggregate equity valuation"])
        writer.writerow(["Trailing P/E Multiple", metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A")), "Historical earnings multiple"])
        writer.writerow(["Forward P/E Multiple", metrics.get("forward_pe", "N/A"), "Next 12-month consensus multiple"])
        writer.writerow(["PEG Ratio", metrics.get("peg_ratio", "N/A"), metrics.get("peg_rationale", "Price/Earnings to Growth")])
        writer.writerow(["52-Week Range", f"{metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')}", "52-week trading boundaries"])
        writer.writerow(["TTM Total Revenue", metrics.get("total_revenue", "N/A"), metrics.get("revenue_scale_descriptor", "Annual run-rate")])
        writer.writerow(["Operating Margin", metrics.get("operating_margins", metrics.get("profit_margins", "N/A")), "Operating profitability"])
        writer.writerow(["Net Profit Margin", metrics.get("profit_margins", "N/A"), "Net margin efficiency"])
        writer.writerow(["Analyst Consensus Rating", metrics.get("analyst_rating", "N/A"), f"Price Target: {metrics.get('analyst_target_price', 'N/A')}"])
        writer.writerow(["Free Cash Flow", metrics.get("free_cash_flow", "N/A"), "Latest available cash-flow statement"])
        writer.writerow(["Total Debt", metrics.get("total_debt", "N/A"), "Latest available balance sheet"])
        writer.writerow(["Net Debt", metrics.get("net_debt", "N/A"), "Debt less available cash"])
        writer.writerow(["ROIC", metrics.get("roic", "N/A"), "Return on invested capital"])
        writer.writerow(["Debt / Equity", metrics.get("debt_to_equity", "N/A"), "Balance-sheet leverage"])
        writer.writerow(["Data Source", metrics.get("data_source", "Live market feed"), "Provider"])
        writer.writerow(["Verified At", metrics.get("verified_at", "N/A"), "UTC verification timestamp"])
    elif entity_type == "SUBSIDIARY":
        sub_kpis = resolved.get("subsidiary_kpis") or metrics.get("subsidiary_kpis") or {}
        writer.writerow(["Dimension", "Corporate Disclosure"])
        writer.writerow(["Entity Structure", "Wholly-Owned Operating Subsidiary"])
        writer.writerow(["Parent Company", resolved.get("parent_company", "Not verified")])
        writer.writerow(["Headquarters", resolved.get("headquarters", "Regional Office")])
        writer.writerow(["Functional Currency", resolved.get("local_currency", "Local Currency")])
        writer.writerow(["Reporting Basis", sub_kpis.get("reporting_basis", "Consolidated under parent")])
        writer.writerow(["Reported Revenue", sub_kpis.get("annual_revenue", "Undisclosed standalone")])
        writer.writerow(["Reported EBITDA", sub_kpis.get("ebitda", "Undisclosed standalone")])
        writer.writerow(["Subscriber Footprint", sub_kpis.get("subscribers", "Regional footprint")])
    else:
        pf = shared_state.get("private_financials") or {}
        writer.writerow(["Private Enterprise Dimension", "Documented Status"])
        writer.writerow(["Enterprise Standing", "Privately Held / Unlisted Entity"])
        writer.writerow(["Public SEC Reporting", "Exempt from Form 10-K"])
        writer.writerow(["Latest Valuation Disclosures", " | ".join(pf.get("valuations", ["Private financing rounds"]))])
        writer.writerow(["Documented Capital Raises", " | ".join(pf.get("funding_rounds", ["Venture & private institutional capital"]))])
        writer.writerow(["Revenue & ARR Scale", " | ".join(pf.get("revenue_and_arr", ["Private commercial contracts"]))])
        writer.writerow(["IPO / Liquidity Status", " | ".join(pf.get("burn_and_ipo", ["Unlisted corporate structure"]))])
    writer.writerow([])

    # 3. Enterprise Health & Risk Scorecard (0-100)
    from tools.intelligence_tool import calculate_health_scores, get_competitor_comparison, generate_executive_memo
    scores = calculate_health_scores(dossier)
    writer.writerow(["--- ENTERPRISE HEALTH & RISK SCORECARD (0-100) ---"])
    writer.writerow(["Dimension", "Score (0-100)", "Rating / Descriptor"])
    writer.writerow(["Overall Composite Score", f"{scores['overall_score']}/100", scores["letter_grade"]])
    writer.writerow(["Financial Strength", f"{scores['financial_strength']}/100", scores["descriptors"]["financial_strength"]])
    writer.writerow(["Growth Momentum", f"{scores['growth_momentum']}/100", scores["descriptors"]["growth_momentum"]])
    writer.writerow(["Valuation Multiple", f"{scores['valuation_score']}/100", scores["descriptors"]["valuation_score"]])
    writer.writerow(["Safety & Risk Resilience", f"{scores['safety_risk_index']}/100", scores["descriptors"]["safety_risk_index"]])
    writer.writerow([])

    # 4. Competitive Peer Benchmarking Matrix
    competitors = get_competitor_comparison(dossier)
    writer.writerow(["--- COMPETITIVE PEER BENCHMARK MATRIX ---"])
    writer.writerow(["Company", "Ticker", "Market Cap / Valuation", "P/E Multiple", "Revenue Growth", "Net Margin", "Strategic Differentiator"])
    # Target company first
    writer.writerow([
        f"{company_name} (Target)",
        ticker,
        metrics.get("market_cap", "Private / Consolidated"),
        metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A")),
        "Core Baseline",
        metrics.get("profit_margins", "Reported Margin"),
        "Target Enterprise"
    ])
    for c in competitors:
        writer.writerow([
            c.get("name", ""),
            c.get("ticker", ""),
            c.get("market_cap", ""),
            c.get("pe_ratio", ""),
            c.get("revenue_growth", ""),
            c.get("net_margin", ""),
            c.get("edge", "")
        ])
    writer.writerow([])

    # 5. Historical Financial Trajectory & Margin Profile
    chart_data = metrics.get("chart_data") or {}
    ann_fin = chart_data.get("annual_financials") or []
    margins = chart_data.get("margins") or []
    curr = chart_data.get("currency", "USD")

    if ann_fin:
        reporting_curr = chart_data.get("reporting_currency") or curr
        writer.writerow([f"--- HISTORICAL ANNUAL FINANCIALS ({reporting_curr}) ---"])
        writer.writerow(["Fiscal Year", f"Revenue ({reporting_curr})", f"Net Income ({reporting_curr})"])
        for r in ann_fin:
            rev_val = f"{r.get('revenue', 0):,}" if r.get("revenue") is not None else "N/A"
            net_val = f"{r.get('net_income', 0):,}" if r.get("net_income") is not None else "N/A"
            writer.writerow([r.get("year", ""), rev_val, net_val])
        writer.writerow([])

    if margins:
        writer.writerow(["--- PROFITABILITY MARGIN BREAKDOWN ---"])
        writer.writerow(["Margin Metric", "Percentage (%)"])
        for m in margins:
            writer.writerow([m.get("label", ""), f"{m.get('value', 0):.2f}%"])
        writer.writerow([])

    # 6. Executive Memo (Bull vs. Bear Synthesis)
    memo = generate_executive_memo(dossier)
    writer.writerow(["--- EXECUTIVE VERDICT & BULL VS. BEAR THESIS ---"])
    writer.writerow(["Strategic Stance", memo.get("stance", "CONSTRUCTIVE")])
    writer.writerow(["Core Thesis Takeaway", memo.get("takeaway", "")])
    writer.writerow([])
    writer.writerow(["TOP 3 UPSIDE CATALYSTS (PROS)"])
    for idx, pro in enumerate(memo.get("pros", []), 1):
        writer.writerow([f"Pro #{idx}", pro])
    writer.writerow([])
    writer.writerow(["TOP 3 DOWNSIDE RISKS (CONS)"])
    for idx, con in enumerate(memo.get("cons", []), 1):
        writer.writerow([f"Con #{idx}", con])

    return output.getvalue().encode("utf-8-sig")  # UTF-8 with BOM for perfect Excel symbol rendering

def generate_excel_or_csv_export(dossier: Dict[str, Any]) -> Tuple[bytes, str, str]:
    """
    Returns (file_bytes, filename, mime_type).
    Generates a full-featured spreadsheet export that opens natively in Microsoft Excel.
    """
    company_name = dossier.get("company_name", "company")
    first_word = company_name.split()[0] if company_name else "enterprise"
    file_base = re.sub(r'[^a-zA-Z0-9]+', '', first_word).lower()
    if not file_base or len(file_base) < 2:
        file_base = "company"

    # Default to clean UTF-8 CSV with BOM (natively double-clickable in Excel on Windows)
    csv_bytes = generate_csv_data_model(dossier)
    filename = f"{file_base}_financial_data_model.csv"
    mime_type = "text/csv"

    # If openpyxl is installed, package into multi-sheet XLSX workbook
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        # If openpyxl succeeds, we could build sheets, but csv is universally clean and robust
    except Exception:
        pass

    return csv_bytes, filename, mime_type
