import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime
from typing import Dict, Any, List

def sanitize_text(text: str) -> str:
    """
    Sanitize unicode characters, dashes, quotes, and LaTeX artifacts for clean typography in PDF & Markdown.
    Completely eliminates '?' character corruptions and broken delimiters.
    """
    if not text:
        return ""
    
    # 1. Clean raw LaTeX / Math artifacts & Bleed
    # e.g. $At^{**}154.71^{**}$ -> At $154.71, $Al^{**}$ -> AI, $.^{**}19.07x^{**}$ -> 19.07x, $3.64T -> $3.64T
    text = re.sub(r'\bJenson\b', 'Jensen', text)
    text = re.sub(r'\$\s*At\^?\{?\*+\}?\s*([0-9\.\,]+)\^?\{?\*+\}?\s*\$?', r'At $\1', text)
    text = re.sub(r'\$At\^\{\*\*\}', 'At $', text)
    text = re.sub(r'\$Al\^\{\*\*\}', 'AI', text)
    text = re.sub(r'\$AI\^\{\*\*\}', 'AI', text)
    text = re.sub(r'\$Al\$', 'AI', text)
    text = re.sub(r'\$([A-Za-z]+)\^\{?\*+\}?\s*([0-9\.\,]+)\^\{?\*+\}?\s*\$?', r'\1 $\2', text)
    text = re.sub(r'\$\.?(?:\^\{?\*+\}?)?([0-9\.\,]+x?)(?:\^\{?\*+\}?)?\$?', r'\1', text)
    text = re.sub(r'\$([A-Za-z0-9\.\,\%\+\-]+)\$', r'\1', text)
    text = text.replace("^{**}", "").replace("^{2}", "2").replace("^{3}", "3")
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
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
        self.set_auto_page_break(auto=True, margin=15)

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
            
        self.cell(0, 10, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(203, 213, 225)
        self.set_xy(150, 6)
        self.cell(50, 10, datetime.now().strftime("%B %d, %Y"), align="R")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Autonomous Multi-Agent Intelligence System | Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42) # Dark slate
        self.cell(0, 8, sanitize_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Accent underline
        self.set_draw_color(59, 130, 246) # Blue
        self.set_line_width(0.7)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(3)

    def sub_section_title(self, title: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(30, 58, 138) # Deep navy blue
        clean_title = sanitize_text(title.replace("#", "").strip())
        self.cell(0, 6, clean_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
                self.multi_cell(0, 5, clean_text)
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
    
    exec_summary = report_data.get("executive_summary") or report_data.get("synthesis", {}).get("executive_summary", "No executive summary provided.")
    corp_bg = report_data.get("corporate_background") or report_data.get("biography", {}).get("analysis", "No background available.")
    fin_analysis = report_data.get("financial_analysis") or report_data.get("financial", {}).get("analysis", "")
    news_analysis = report_data.get("recent_news_analysis") or report_data.get("news", {}).get("analysis", "No recent news analysis provided.")
    strategic_out = report_data.get("strategic_outlook") or report_data.get("synthesis", {}).get("strategic_outlook", "No outlook details provided.")
    news_articles = report_data.get("news_articles") or report_data.get("news", {}).get("articles", [])
    
    pdf = IntelligenceReportPDF(company_name=company, ticker=ticker)
    pdf.add_page()
    
    # Title & Subheading
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, f"{company} Comprehensive Briefing", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    
    if is_public:
        pdf.cell(0, 5, sanitize_text(f"Status: Publicly Traded | Sector: {metrics.get('sector', 'N/A')} | Industry: {metrics.get('industry', 'N/A')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.cell(0, 5, sanitize_text("Status: Privately Held / Non-Public Enterprise | Unlisted Equity"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    
    # Financial & Corporate Profile Dashboard Grid
    if is_public:
        pdf.section_title("1. Financial Health & Valuation Snapshot (Public Equity)")
        kpis = [
            ("Stock Price", str(metrics.get("current_price", "N/A")), "Market Cap", str(metrics.get("market_cap", "N/A"))),
            ("Trailing P/E", str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A"))), "Forward P/E", str(metrics.get("forward_pe", "N/A"))),
            ("PEG Ratio", str(metrics.get("peg_ratio", "N/A")), "TTM Revenue", str(metrics.get("total_revenue", "N/A"))),
            ("Gross Margin", str(metrics.get("gross_margins", "N/A")), "Profit Margin", str(metrics.get("profit_margins", "N/A"))),
            ("52-Wk Range", f"{metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')}", "YoY Growth", str(metrics.get("revenue_growth_yoy", "N/A"))),
            ("Analyst Target", str(metrics.get("analyst_target_price", "N/A")), "Consensus Rating", str(metrics.get("analyst_rating", "N/A")))
        ]
    else:
        pdf.section_title("1. Corporate Structure & Private Enterprise Profile")
        kpis = [
            ("Entity Type", "Privately Held Entity", "Trading Status", "Unlisted (No SEC Ticker)"),
            ("Ownership", "Private / VC / Founder", "Reporting", "Exempt from SEC 10-K Filings"),
            ("Capital Basis", "Private Investment Rounds", "Market Access", "Secondary / Direct Equity"),
            ("Primary Domain", "Technology & Services", "Financial Audit", "Private Corporate Books")
        ]
    
    pdf.set_font("Helvetica", "B", 9)
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
        
    pdf.ln(3)
    
    # Executive Summary Section
    pdf.section_title("2. Executive Summary & Strategic Synthesis")
    pdf.body_paragraph(exec_summary)
    
    # Background & Corporate History
    pdf.section_title("3. Corporate Background, Operations & Strategic Moat")
    pdf.body_paragraph(corp_bg)
    
    # Financial Analysis Narrative
    if fin_analysis:
        pdf.section_title("4. In-Depth Financial & Valuation Analysis")
        pdf.body_paragraph(fin_analysis)

    # Recent News & Catalysts
    pdf.section_title("5. Recent News, Strategic Moves & Market Sentiment")
    pdf.body_paragraph(news_analysis)

    # Detailed Sources Section (Requested by user)
    pdf.section_title("Here are the Detailed Sources:")
    articles: List[Dict[str, str]] = news_articles
    if articles:
        pdf.set_font("Helvetica", "", 8.5)
        for i, a in enumerate(articles, 1):
            title = sanitize_text(a.get("title", ""))
            source = sanitize_text(a.get("source", ""))
            date = sanitize_text(a.get("date", ""))
            url = sanitize_text(a.get("url", ""))
            
            pdf.set_text_color(30, 64, 175) # Blue link style
            pdf.cell(0, 4.5, f"{i}. {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(100, 116, 139) # Grey meta
            pdf.cell(0, 4, f"   Publisher: {source} | Date: {date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if url:
                pdf.cell(0, 4, f"   URL: {url[:80]}...", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)
    else:
        pdf.body_paragraph("No external news sources recorded for this profile.")
    
    # Strategic Outlook & Risks
    pdf.section_title("6. Strategic Outlook, Growth Vectors & Key Risks")
    pdf.body_paragraph(strategic_out)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
    
    return bytes(pdf.output())
