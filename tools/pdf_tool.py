import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime
from typing import Dict, Any, List, Optional
from tools.intelligence_tool import calculate_health_scores, get_competitor_comparison, generate_executive_memo

def sanitize_text(text: str) -> str:
    """
    Sanitize unicode characters, dashes, quotes, Markdown bold/code tokens, and LaTeX artifacts
    for clean typography in rendered PDF output.
    Completely eliminates '?', stray '$', '**', '^{}', and broken math delimiters.
    """
    if not text:
        return ""
    
    # 1. Clean raw LaTeX / Escaped Currency / Math artifacts while preserving valid currency ($154.71, $3.78T, $115.8 billion)
    # Normalize Unicode fullwidth/small dollar signs and unescape backslashes FIRST
    text = text.replace("\uFF04", "$").replace("\uFE69", "$")
    text = re.sub(r'[\\\uFF3C\u2216]+\s*\$', '$', text)
    text = re.sub(
        r'\$+\s*(?:\\(?:text|mathrm|mathbf|textbf|mathit)\{)?\s*(P\s*/\s*E|PEG|EPS|EV\s*/\s*EBITDA|P\s*/\s*S|P\s*/\s*B|ROE|ROA|FCF|ARR|YoY|QoQ|EBITDA)\s*\}?\s*\$+',
        r'\1', text, flags=re.IGNORECASE
    )
    text = re.sub(r'[\\\uFF3C\u2216]+([%&_\*#])', r'\1', text)
    text = re.sub(r'\\(?=[0-9\$])', '', text)
    # Unwrap LaTeX wrapper commands BEFORE stripping $...$ so $\text{P/E}$ -> $P/E$ -> P/E
    text = re.sub(r'\\(?:text|mathrm|mathbf|textbf|mathit|operatorname)\{([^\}]*)\}', r'\1', text)
    text = text.replace("\\times", "x").replace("\\approx", "~")
    text = re.sub(r'\bJenson\b', 'Jensen', text)
    text = re.sub(r'\bOpenAl\b', 'OpenAI', text)
    text = re.sub(r'\bChief\s+Scientist\s+Officer\b', 'Chief Scientist', text, flags=re.IGNORECASE)
    # Fix erratic mid-sentence capitalization after common adverbs (e.g. "heavily Fixated" -> "heavily fixated")
    text = re.sub(
        r'\b(heavily|strongly|deeply|closely|largely|widely|rapidly|sharply|primarily|increasingly|remains|remain)\s+'
        r'(Fixated|Focused|Driven|Positioned|Weighted|Exposed|Skewed|Anchored|Centered|Watched|Scrutinized|Pressured)\b',
        lambda m: f"{m.group(1)} {m.group(2).lower()}",
        text
    )
    # Handle ${}^{**}9.72x^{**}$ and {}^{**}9.72x^{**}
    text = re.sub(r'\$\s*\{\s*\}\s*\^\{\*+\}\s*([^\$\n]+?)\s*(?:\^\{\*+\})?\s*\$', r'\1', text)
    text = re.sub(r'\{\s*\}\s*\^\{\*+\}\s*([^\s\$\n]+?)\s*(?:\^\{\*+\})?', r'\1', text)
    text = re.sub(r'\$\s*At\^?\{?\*+\}?\s*([0-9\.\,]+)\^?\{?\*+\}?\s*\$?', r'At $\1', text)
    text = re.sub(r'\$At\^\{\*\*\}', 'At $', text)
    text = re.sub(r'\$Al\^\{\*\*\}', 'AI', text)
    text = re.sub(r'\$AI\^\{\*\*\}', 'AI', text)
    text = re.sub(r'\$Al\$', 'AI', text)
    # Strip ALL non-currency inline math $...$ (e.g. $P/E$, $P/E^{**}$, $P / E$, $EPS$, $AI$)
    text = re.sub(r'\$(?![0-9])([^\$\n]{1,40}?)\$', r'\1', text)
    # Strip $9.72x$, $48.9%$, $.^{**}19.07x^{**}$
    text = re.sub(r'\$\.?(?:\^\{\*+\})?\s*([0-9\.\,]+[xX%])(?:\^\{\*+\})?\s*\$?', r'\1', text)
    text = re.sub(r'\$([A-Za-z]+)\^\{?\*+\}?\s*([0-9\.\,]+)\^\{?\*+\}?\s*\$?', r'\1 $\2', text)
    text = re.sub(r'\^\{\*+\}', '', text)
    text = re.sub(r'\{\s*\}', '', text)
    text = text.replace("^{**}", "").replace("^{2}", "2").replace("^{3}", "3")
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    # Strip raw Markdown bold/italic/code delimiters for clean FPDF plain-text rendering
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = text.replace("**", "")
    # Remove any stray '$' NOT followed by a digit (currency like $3.75T, $115.8 billion stays intact!)
    text = re.sub(r'\$(?![0-9])', '', text)
    # Fix accidental double periods (e.g. "November 2026..") while preserving ellipses ("...")
    text = re.sub(r'(?<!\.)\.\.(?!\.)', '.', text)
    # Deduplicate accidental consecutive repeated words (e.g. "formal formal", "the the")
    text = re.sub(
        r'\b(formal|the|a|an|in|on|at|to|of|for|with|by|as|is|are|was|were|be|no|not|and|or|from|that|this|its|their|current|verified|public|private|annual|quarterly)\s+\1\b',
        r'\1', text, flags=re.IGNORECASE
    )
    # Clean duplicated PEG phrasing if present
    text = re.sub(r'\bWith\s+a\s+(PEG\s+ratio\s+of\s+[0-9\.]+)\s*,\s*\1\b', r'A \1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bcanonical\b', 'verified', text, flags=re.IGNORECASE)
    text = re.sub(r'\bdouble-digit\s+scale\b(?=.*\$[1-9][0-9]{2}(?:\.[0-9]+)?B)', 'triple-digit billion-dollar scale', text, flags=re.IGNORECASE)
    text = re.sub(r'\bdouble-digit\s+scale\s*(?:of|at)?\s*\$([1-9][0-9]{2})', r'triple-digit billion-dollar scale of $\1', text, flags=re.IGNORECASE)
    
    # 2. Comprehensive Unicode Dash & Hyphen mapping (prevents '?' in date ranges e.g. 1999-2006, Nov 16-17)
    dash_chars = [
        "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", 
        "\u2212", "\ufe58", "\ufe63", "\uff0d", "\u00ad"
    ]
    for d in dash_chars:
        text = text.replace(d, "-")

    # 3. Comprehensive Quotes & Typographic symbols mapping
    replacements = {
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201a": "'",   # low single quote
        "\u201b": "'",   # high single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u201e": '"',   # low double quote
        "\u201f": '"',   # high double quote
        "\u2032": "'",   # prime
        "\u2033": '"',   # double prime
        "\u2022": "* ",  # bullet
        "\u25cf": "* ",  # black circle bullet
        "\u25cb": "* ",  # white circle
        "\u25aa": "* ",  # black square
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\u200b": "",    # zero-width space
        "\u200c": "",    # zero-width non-joiner
        "\u200d": "",    # zero-width joiner
        "\ufeff": "",    # byte order mark
        "\u20b9": "INR ", # Indian Rupee
        "\u20ac": "EUR ", # Euro
        "\u00a3": "GBP ", # Pound
        "\u00a5": "JPY ", # Yen
        "\u2248": "~",   # approximately equal
        "\u2264": "<=",  # less than or equal
        "\u2265": ">=",  # greater than or equal
        "\u2192": "->",  # right arrow
        "\u2190": "<-",  # left arrow
        "\u2194": "<->", # left-right arrow
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 4. Safe character filtering for PDF latin-1 font table
    clean_chars = []
    for char in text:
        cp = ord(char)
        if cp < 128:
            clean_chars.append(char)
        elif 160 <= cp <= 255:
            clean_chars.append(char)
        else:
            clean_chars.append(" ")
            
    return "".join(clean_chars)

class IntelligenceReportPDF(FPDF):
    def __init__(self, company_name: str, ticker: str):
        super().__init__()
        self.company_name = sanitize_text(company_name)
        self.ticker = sanitize_text(ticker)
        # Top margin 28mm clears the 22mm header banner; bottom margin 20mm clears the -15mm footer cleanly
        self.set_margins(left=10, top=28, right=10)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Header banner
        self.set_fill_color(30, 41, 59) # Slate navy
        self.rect(0, 0, 210, 22, "F")
        
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 6)
        label = f"INTELLIGENCE DOSSIER: {self.company_name.upper()}"
        if self.ticker and self.ticker != "PRIVATE / UNLISTED":
            label += f" ({self.ticker})"
        else:
            label += " [PRIVATE ENTERPRISE]"
            
        self.cell(135, 10, label[:72], new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(203, 213, 225)
        self.set_xy(150, 6)
        self.cell(50, 10, datetime.now().strftime("%B %d, %Y"), align="R")
        # Reset cursor cleanly to top-left body margin so automatic page breaks mid-paragraph never collide
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Autonomous Multi-Agent Intelligence System | Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        # Widow/orphan guard: move to next page if insufficient space below heading
        if self.get_y() > self.page_break_trigger - 24:
            self.add_page()
        self.ln(4)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42) # Dark slate
        self.multi_cell(0, 7.5, sanitize_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Accent underline
        self.set_draw_color(59, 130, 246) # Blue
        self.set_line_width(0.7)
        self.line(self.l_margin, self.get_y(), self.l_margin + 190, self.get_y())
        self.ln(3)

    def sub_section_title(self, title: str):
        if self.get_y() > self.page_break_trigger - 18:
            self.add_page()
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(30, 58, 138) # Deep navy blue
        clean_title = sanitize_text(title.replace("#", "").strip())
        self.multi_cell(0, 6, clean_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body_paragraph(self, text: str):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(1.5)
                continue
            if line.startswith("#"):
                self.sub_section_title(line)
            else:
                self.set_font("Helvetica", "", 9.5)
                self.set_text_color(51, 65, 85) # Slate text
                clean_text = sanitize_text(line)
                # Page-break-inside: avoid for short/medium paragraphs (<= 6 wrapped lines) to prevent awkward splits/overlaps
                try:
                    wrapped = self.multi_cell(0, 5, clean_text, dry_run=True, output="LINES")
                    needed_h = len(wrapped) * 5 + 2
                    if len(wrapped) <= 6 and (self.get_y() + needed_h > self.page_break_trigger):
                        self.add_page()
                except Exception:
                    pass
                self.set_x(self.l_margin)
                self.multi_cell(0, 5, clean_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(1)

def generate_pdf_report(
    report_data: Dict[str, Any],
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate an in-depth, structured executive PDF report.
    Returns bytes in-memory without creating files on disk unless output_path is explicitly provided.
    """
    company = sanitize_text(report_data.get("company_name", report_data.get("shared_state", {}).get("company_name", "Target Company")))
    ticker = sanitize_text(report_data.get("ticker", report_data.get("shared_state", {}).get("ticker", "PRIVATE / UNLISTED")))
    metrics = report_data.get("metrics", report_data.get("shared_state", {}).get("metrics", {}))
    is_public = report_data.get("is_public", report_data.get("shared_state", {}).get("is_public", True))
    resolved_entity = report_data.get("resolved_entity") or report_data.get("shared_state", {}).get("resolved_entity") or {}
    entity_type = report_data.get("entity_type") or resolved_entity.get("entity_type") or ("PUBLIC" if is_public else "PRIVATE")
    
    exec_summary = report_data.get("executive_summary") or report_data.get("synthesis", {}).get("executive_summary", "No executive summary provided.")
    corp_bg = report_data.get("corporate_background") or report_data.get("biography", {}).get("analysis", "No background available.")
    fin_analysis = report_data.get("financial_analysis") or report_data.get("financial", {}).get("analysis", "")
    news_analysis = report_data.get("recent_news_analysis") or report_data.get("news", {}).get("analysis", "No recent news analysis provided.")
    strategic_out = report_data.get("strategic_outlook") or report_data.get("synthesis", {}).get("strategic_outlook", "No outlook details provided.")
    news_articles = report_data.get("news_articles") or report_data.get("news", {}).get("articles", [])
    
    pdf = IntelligenceReportPDF(company_name=company, ticker=ticker)
    pdf.add_page()
    
    # Title & Subheading
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 8.5, f"{company} Comprehensive Briefing", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(100, 116, 139)
    
    if entity_type == "PUBLIC" and is_public:
        pdf.multi_cell(0, 5, sanitize_text(f"Status: Publicly Traded | Sector: {metrics.get('sector', 'N/A')} | Industry: {metrics.get('industry', 'N/A')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    elif entity_type == "SUBSIDIARY":
        parent_co = resolved_entity.get("parent_company") or metrics.get("parent_company") or "Parent Holding Group"
        hq = resolved_entity.get("headquarters") or metrics.get("headquarters") or "Regional Market"
        sector = resolved_entity.get("sector") or metrics.get("sector") or "Telecommunications & Services"
        pdf.multi_cell(0, 5, sanitize_text(f"Status: Wholly-Owned Operating Subsidiary | Parent: {parent_co} | HQ: {hq} | Sector: {sector}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.multi_cell(0, 5, sanitize_text("Status: Privately Held / Non-Public Enterprise | Unlisted Equity"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    
    # Financial & Corporate Profile Dashboard Grid
    if entity_type == "PUBLIC" and is_public:
        pdf.section_title("1. Financial Health & Valuation Snapshot (Public Equity)")
        kpis = [
            ("Stock Price", str(metrics.get("current_price", "N/A")), "Market Cap", str(metrics.get("market_cap", "N/A"))),
            ("Trailing P/E", str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A"))), "Forward P/E", str(metrics.get("forward_pe", "N/A"))),
            ("PEG Ratio", str(metrics.get("peg_ratio", "N/A")), "TTM Revenue", str(metrics.get("total_revenue", "N/A"))),
            ("Gross Margin", str(metrics.get("gross_margins", "N/A")), "Profit Margin", str(metrics.get("profit_margins", "N/A"))),
            ("52-Wk Range", f"{metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')}", "YoY Growth", str(metrics.get("revenue_growth_yoy", "N/A"))),
            ("Analyst Target", str(metrics.get("analyst_target_price", "N/A")), "Consensus Rating", str(metrics.get("analyst_rating", "N/A")))
        ]
    elif entity_type == "SUBSIDIARY":
        pdf.section_title("1. Subsidiary Ownership & Operating Profile")
        sub_kpis = resolved_entity.get("subsidiary_kpis") or metrics.get("subsidiary_kpis") or {}
        parent_co = resolved_entity.get("parent_company") or metrics.get("parent_company") or "Parent Group"
        legal_name = resolved_entity.get("legal_entity_name") or company
        currency = resolved_entity.get("local_currency") or "Local"
        hq = resolved_entity.get("headquarters") or "Regional"
        rev_short = (sub_kpis.get("annual_revenue") or f"Consolidated under {parent_co}")[:34]
        subs_short = (sub_kpis.get("subscribers") or "Regional Market Leader")[:34]
        credit_short = (sub_kpis.get("credit_rating") or f"Backed by {parent_co}")[:34]
        kpis = [
            ("Entity Type", "Wholly-Owned Subsidiary", "Parent Company", parent_co[:34]),
            ("Legal Entity", legal_name[:34], "Headquarters", hq[:34]),
            ("Currency", f"{currency} (Consolidated)", "Reported Rev", rev_short),
            ("Scale / Subs", subs_short, "Credit / Backing", credit_short)
        ]
    else:
        pdf.section_title("1. Corporate Structure & Private Enterprise Profile")
        kpis = [
            ("Entity Type", "Privately Held Entity", "Trading Status", "Unlisted (No SEC Ticker)"),
            ("Ownership", "Private / Strategic / Founder", "Reporting", "Exempt from SEC 10-K Filings"),
            ("Capital Basis", "Private Financing Rounds", "Market Access", "Secondary / Direct Equity"),
            ("Primary Domain", "Technology & Services", "Financial Audit", "Private Corporate Books")
        ]
    
    pdf.set_font("Helvetica", "B", 8.5)
    for row in kpis:
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(32, 7, sanitize_text(row[0]), border=1, fill=True)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(63, 7, sanitize_text(row[1]), border=1)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(32, 7, sanitize_text(row[2]), border=1, fill=True)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(63, 7, sanitize_text(row[3]), border=1)
        pdf.ln(7)
        
    pdf.ln(2)

    # 1b. Enterprise Health & Risk Scorecard (0-100)
    scores = report_data.get("health_scorecard") or calculate_health_scores(report_data)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 5.5, sanitize_text(f"ENTERPRISE HEALTH & RISK SCORECARD: {scores['overall_score']}/100 ({scores['letter_grade']})"), border=1, fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    score_headers = [
        ("Overall Score", f"{scores['overall_score']}/100"),
        ("Financial Health", f"{scores['financial_strength']}/100"),
        ("Growth Score", f"{scores['growth_momentum']}/100"),
        ("Valuation Attractiveness", f"{scores['valuation_score']}/100"),
        ("Safety & Risk Index", f"{scores['safety_risk_index']}/100"),
    ]
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_text_color(30, 41, 59)
    for title, val in score_headers:
        pdf.cell(38, 5, sanitize_text(f"{title}: {val}"), border=1, fill=True, align="C")
    pdf.ln(6)
    
    # Executive Summary Section
    pdf.section_title("2. Executive Summary & Strategic Synthesis")

    # 2b. Executive Verdict Memo (Bull vs. Bear Synthesis)
    memo = report_data.get("executive_memo") or generate_executive_memo(report_data)
    if memo:
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(190, 5.5, sanitize_text(f"STRATEGIC STANCE: {memo.get('stance', 'CONSTRUCTIVE')} -- {memo.get('headline', '')}"), border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("Helvetica", "I", 7.8)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(190, 4, sanitize_text(f"Core Takeaway: {memo.get('takeaway', '')}"), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(22, 101, 52) # Dark green
        for pro in memo.get("pros", []):
            pdf.multi_cell(190, 3.8, sanitize_text(f"  [+] Upside Driver: {pro}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
        pdf.set_text_color(153, 27, 27) # Dark red
        for con in memo.get("cons", []):
            pdf.multi_cell(190, 3.8, sanitize_text(f"  [-] Risk Vector: {con}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2.5)

    pdf.body_paragraph(exec_summary)
    
    # Background & Corporate History
    pdf.section_title("3. Corporate Background, Operations & Strategic Moat")
    pdf.body_paragraph(corp_bg)
    
    # Financial Analysis Narrative + Native Vector Charts (Public Equities)
    if fin_analysis:
        pdf.section_title("4. In-Depth Financial & Valuation Analysis")
        pdf.body_paragraph(fin_analysis)

        # 4b. Competitive Peer Benchmark Matrix
        competitors = report_data.get("competitor_comparison") or get_competitor_comparison(report_data)
        if competitors:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 5.5, "Competitive Peer Benchmarking Matrix", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(226, 232, 240)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(32, 5, "Company", border=1, fill=True)
            pdf.cell(14, 5, "Ticker", border=1, fill=True)
            pdf.cell(24, 5, "Valuation", border=1, fill=True)
            pdf.cell(15, 5, "P/E", border=1, fill=True)
            pdf.cell(16, 5, "Growth", border=1, fill=True)
            pdf.cell(16, 5, "Margin", border=1, fill=True)
            pdf.cell(73, 5, "Strategic Differentiator / Moat", border=1, fill=True)
            pdf.ln(5)
            
            # Target Row
            pdf.set_font("Helvetica", "B", 6.8)
            pdf.set_fill_color(239, 246, 255)
            pdf.set_text_color(30, 64, 175)
            pdf.cell(32, 5, sanitize_text(f"{company[:18]} (Target)"), border=1, fill=True)
            pdf.cell(14, 5, sanitize_text(ticker[:6]), border=1, fill=True)
            pdf.cell(24, 5, sanitize_text(str(metrics.get("market_cap", "Baseline"))[:12]), border=1, fill=True)
            pdf.cell(15, 5, sanitize_text(str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A")))[:8]), border=1, fill=True)
            pdf.cell(16, 5, sanitize_text(str(metrics.get("revenue_growth_yoy", "Baseline"))[:8]), border=1, fill=True)
            pdf.cell(16, 5, sanitize_text(str(metrics.get("profit_margins", "Reported"))[:8]), border=1, fill=True)
            pdf.cell(73, 5, "Target Enterprise Moat & Ecosystem", border=1, fill=True)
            pdf.ln(5)

            # Peer Rows
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(51, 65, 85)
            for c in competitors:
                pdf.cell(32, 5, sanitize_text(c.get("name", "")[:20]), border=1)
                pdf.cell(14, 5, sanitize_text(c.get("ticker", "")[:6]), border=1)
                pdf.cell(24, 5, sanitize_text(c.get("market_cap", "")[:12]), border=1)
                pdf.cell(15, 5, sanitize_text(c.get("pe_ratio", "")[:8]), border=1)
                pdf.cell(16, 5, sanitize_text(c.get("revenue_growth", "")[:8]), border=1)
                pdf.cell(16, 5, sanitize_text(c.get("net_margin", "")[:8]), border=1)
                raw_edge = c.get("edge", "")
                if len(raw_edge) > 65:
                    trimmed = raw_edge[:62].rsplit(' ', 1)[0] + "..."
                else:
                    trimmed = raw_edge
                pdf.cell(73, 5, sanitize_text(trimmed), border=1)
                pdf.ln(5)
            pdf.ln(2.5)

        if entity_type == "PUBLIC" and is_public and metrics.get("chart_data"):
            try:
                from tools.chart_tool import render_financial_charts_to_pdf
                render_financial_charts_to_pdf(pdf, metrics.get("chart_data"), company, ticker)
            except Exception:
                pass

    # Recent News & Catalysts
    pdf.section_title("5. Recent News, Strategic Moves & Market Sentiment")
    pdf.body_paragraph(news_analysis)

    # Detailed Sources Section (Clean clickable hyperlinks without ugly raw URL line-wraps)
    pdf.section_title("Here are the Detailed Sources:")
    articles: List[Dict[str, str]] = news_articles
    if articles:
        for i, a in enumerate(articles, 1):
            if pdf.get_y() > pdf.page_break_trigger - 18:
                pdf.add_page()
            title = sanitize_text(a.get("title", ""))
            source = sanitize_text(a.get("source", "Verified Source"))
            date = sanitize_text(a.get("date", "Recent"))
            url = (a.get("url") or "").strip()

            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(30, 64, 175) # Blue link style
            pdf.multi_cell(0, 4.5, f"{i}. {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(100, 116, 139) # Grey meta
            pdf.multi_cell(0, 4, f"   Publisher: {source} | Date: {date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            if url and url.startswith(("http://", "https://")):
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "U", 8)
                pdf.set_text_color(37, 99, 235)
                pdf.cell(0, 4, f"   Read Article ({source})", link=url, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.8)
    else:
        pdf.body_paragraph("No external news sources recorded for this profile.")
    
    # Strategic Outlook & Risks
    pdf.section_title("6. Strategic Outlook, Growth Vectors & Key Risks")
    pdf.body_paragraph(strategic_out)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
    
    return bytes(pdf.output())
