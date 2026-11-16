from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime
from typing import Dict, Any, List
import os

def sanitize_text(text: str) -> str:
    """Sanitize unicode characters (like en-dashes, em-dashes, smart quotes, bullets) for standard PDF fonts."""
    if not text:
        return ""
    replacements = {
        "\u2013": "-",   # en-dash
        "\u2014": "--",  # em-dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "*",   # bullet
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\u20b9": "INR", # Indian Rupee symbol
        "\u20ac": "EUR", # Euro symbol
        "\u00a3": "GBP", # Pound symbol
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

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
    output_path: str = "reports/intelligence_report.pdf"
) -> str:
    """
    Generate an in-depth, structured executive PDF report.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    company = sanitize_text(report_data.get("company_name", "Target Company"))
    ticker = sanitize_text(report_data.get("ticker", "PRIVATE / UNLISTED"))
    metrics = report_data.get("metrics", {})
    is_public = report_data.get("is_public", True)
    
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
            ("P/E Ratio", str(metrics.get("pe_ratio", "N/A")), "Total Revenue", str(metrics.get("total_revenue", "N/A"))),
            ("52-Wk Range", f"{metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')}", "Profit Margin", str(metrics.get("profit_margins", "N/A"))),
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
    pdf.body_paragraph(report_data.get("executive_summary", "No executive summary provided."))
    
    # Background & Corporate History
    pdf.section_title("3. Corporate Background, Operations & Strategic Moat")
    pdf.body_paragraph(report_data.get("corporate_background", "No background available."))
    
    # Financial Analysis Narrative
    if report_data.get("financial_analysis"):
        pdf.section_title("4. In-Depth Financial & Valuation Analysis")
        pdf.body_paragraph(report_data.get("financial_analysis"))

    # Recent News & Catalysts
    pdf.section_title("5. Recent News, Strategic Moves & Market Sentiment")
    news_text = report_data.get("recent_news_analysis", "No recent news analysis provided.")
    pdf.body_paragraph(news_text)

    # Detailed Sources Section (Requested by user)
    pdf.section_title("Here are the Detailed Sources:")
    articles: List[Dict[str, str]] = report_data.get("news_articles", [])
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
    pdf.body_paragraph(report_data.get("strategic_outlook", "No outlook details provided."))
    
    pdf.output(output_path)
    return output_path
