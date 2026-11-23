import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from agents.supervisor import ResearchSupervisor
import config

console = Console()

def print_banner():
    banner_text = Text()
    banner_text.append("AUTONOMOUS MARKET INTELLIGENCE SYSTEM\n", style="bold cyan")
    banner_text.append("Hierarchical Multi-Agent Architecture (100% Free)\n", style="bold white")
    banner_text.append(f"Active LLM Engine: {config.PROVIDER.upper()} | Cost: $0.00\n", style="green")
    banner_text.append("-" * 65 + "\n", style="dim")
    banner_text.append("Parent Orchestrator  -> Research Director\n", style="magenta")
    banner_text.append("  |-- Subagent 1     -> Financial Analyst      (Tool: Public & Private Market Audits)\n", style="yellow")
    banner_text.append("  |-- Subagent 2     -> News & Sentiment Scout (Tool: Real-Time Verified Feeds)\n", style="blue")
    banner_text.append("  |-- Subagent 3     -> Corporate Biographer   (Tool: Wikipedia & Web Profiles)\n", style="cyan")
    banner_text.append("  `-- Publisher      -> Report Compiler        (Tool: FPDF2 & Markdown)", style="white")

    console.print(Panel(banner_text, border_style="cyan", title="Multi-Agent AI", title_align="left"))

def display_summary(dossier: dict, execution_time: float = 0.0):
    metrics = dossier.get("metrics", {})
    is_public = dossier.get("is_public", True)
    
    # Financial or Corporate Profile Table
    if is_public:
        table = Table(title=f"Market Intelligence Snapshot: {dossier['company_name']} ({dossier['ticker']})", border_style="blue")
        table.add_column("Metric", style="cyan", justify="left")
        table.add_column("Value", style="bold white", justify="left")
        table.add_column("Metric", style="cyan", justify="left")
        table.add_column("Value", style="bold white", justify="left")
        
        table.add_row("Stock Price", str(metrics.get("current_price", "N/A")), "Market Cap", str(metrics.get("market_cap", "N/A")))
        table.add_row("P/E Ratio", str(metrics.get("pe_ratio", "N/A")), "Total Revenue", str(metrics.get("total_revenue", "N/A")))
        table.add_row("52-Week Range", f"{metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')}", "Profit Margin", str(metrics.get("profit_margins", "N/A")))
        table.add_row("Analyst Target", str(metrics.get("analyst_target_price", "N/A")), "Wall St Consensus", str(metrics.get("analyst_rating", "N/A")))
    else:
        table = Table(title=f"Private Enterprise Profile: {dossier['company_name']}", border_style="magenta")
        table.add_column("Attribute", style="magenta", justify="left")
        table.add_column("Corporate Status", style="bold white", justify="left")
        table.add_column("Attribute", style="magenta", justify="left")
        table.add_column("Corporate Status", style="bold white", justify="left")
        
        table.add_row("Entity Classification", "Privately Held Enterprise", "Stock Exchange Listing", "Unlisted (No Public Ticker)")
        table.add_row("Ownership Structure", "Private / VC / Founder", "Reporting Compliance", "Exempt from SEC 10-K Filings")
        table.add_row("Capital Basis", "Private Equity / Revenues", "Market Access", "Secondary / Private Transactions")

    console.print("\n")
    console.print(table)
    
    # Executive Summary Card
    console.print("\n")
    console.print(Panel(
        dossier.get("executive_summary", "No summary."),
        title="[bold green]Executive Summary (Synthesized by Parent Agent)[/bold green]",
        border_style="green"
    ))
    
    # Reports Card
    report_info = (
        f"[bold green]✔ In-Memory Intelligence Dossier Synthesized Successfully![/bold green]\n"
        f"[dim]Execution Time: {execution_time}s | Storage Footprint: 0 files written to disk (Clean In-Memory Mode)[/dim]"
    )
    console.print("\n")
    console.print(Panel(report_info, title="[bold yellow]Dossier Status[/bold yellow]", border_style="yellow"))

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Multi-Agent Market Intelligence System")
    parser.add_argument("--target", "-t", type=str, help="Company name or stock ticker")
    args = parser.parse_args()
    
    target = args.target
    if not target:
        try:
            target = console.input("\n[bold cyan]Enter target company name or stock ticker: [/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Exiting.[/red]")
            sys.exit(0)
            
    if not target:
        console.print("[red]A target company name or stock ticker is required.[/red]")
        return

    supervisor = ResearchSupervisor()
    results = supervisor.run_investigation(target)
    
    display_summary(results["dossier"], results.get("execution_time", 0.0))
    console.print("\n[bold green]Done! Multi-agent pipeline executed successfully.[/bold green]\n")
    console.print("\n[bold green]Done! Multi-agent pipeline executed successfully.[/bold green]\n")

if __name__ == "__main__":
    main()
