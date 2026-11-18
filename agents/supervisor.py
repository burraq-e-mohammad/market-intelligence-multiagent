from agents.base_agent import BaseAgent
from agents.financial_agent import FinancialAnalystAgent
from agents.news_agent import NewsScoutAgent
from agents.biography_agent import BiographyAgent
from agents.qa_critic import QualityAssuranceAgent
from tools.finance_tool import get_financial_metrics
from tools.pdf_tool import generate_pdf_report
from tools.schemas import VerifiedOfficer, parse_officer_string, reconcile_officers
from typing import Dict, Any, Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
import config

class ResearchSupervisor(BaseAgent):
    """
    Parent Agent (Supervisor / Orchestrator):
    Coordinates subagents in parallel, decomposes tasks, aggregates findings, and synthesizes final reports.
    Enforces a strict Single Source of Truth (Shared State) and executes a QA Critic audit prior to publication.
    """
    def __init__(self):
        super().__init__(
            name="Research Supervisor",
            role="Research Director & Intelligence Orchestrator",
            system_prompt="""You are the Research Director at an elite global corporate intelligence firm.
You oversee three specialized analysts: a Financial Analyst, a News & Sentiment Scout, and a Corporate Biographer.
Your job is to synthesize all intelligence into a deep, authoritative, highly structured Executive Briefing and Strategic Outlook.
You MUST enforce 100% internal consistency across all subagent reports and adhere strictly to the Single Source of Truth.
Never write a brief, shallow, or generic summary. Deliver comprehensive, structured paragraphs packed with real facts."""
        )
        
        self.financial_agent = FinancialAnalystAgent()
        self.news_agent = NewsScoutAgent()
        self.biography_agent = BiographyAgent()
        self.qa_critic = QualityAssuranceAgent()

    def run_investigation(self, target_input: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Executes the full hierarchical multi-agent workflow:
        1. Subagents run concurrently in parallel via ThreadPoolExecutor.
        2. Parent Agent synthesizes data into deep Executive Briefing & Strategic Outlook.
        3. Compiles Markdown and PDF reports with detailed verified sources.
        """
        start_time = time.time()
        clean_target = target_input.strip()

        def emit(agent: str, role: str, status: str, message: str):
            elapsed = round(time.time() - start_time, 1)
            event = {
                "time": elapsed,
                "agent": agent,
                "role": role,
                "status": status,
                "message": message
            }
            if progress_callback:
                try:
                    progress_callback(event)
                except Exception:
                    pass

        emit("Research Supervisor", "Parent Director", "started", f"Initiating deep investigation project for '{clean_target}'...")
        print(f"\n[Parent Agent: {self.name}] Initiating research project for '{clean_target}'...")

        # Step 1: Resolve Canonical Entity Classification & Single Source of Truth
        emit("Research Supervisor", "Parent Director", "resolving", f"Resolving canonical entity classification and Single Source of Truth for '{clean_target}'...")
        tool_fin = get_financial_metrics(clean_target)
        is_public = tool_fin.get("is_public", False)
        metrics = tool_fin.get("data", {})
        company_name = metrics.get("company_name", clean_target)
        ticker = metrics.get("symbol", "PRIVATE / UNLISTED")

        shared_state = {
            "company_name": company_name,
            "ticker": ticker,
            "is_public": is_public,
            "metrics": metrics,
            "current_price": metrics.get("current_price", "N/A"),
            "market_cap": metrics.get("market_cap", "N/A"),
            "trailing_pe": metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A")),
            "forward_pe": metrics.get("forward_pe", "N/A"),
            "peg_ratio": metrics.get("peg_ratio", "N/A"),
            "total_revenue": metrics.get("total_revenue", "N/A"),
            "gross_margins": metrics.get("gross_margins", "N/A"),
            "operating_margins": metrics.get("operating_margins", "N/A"),
            "profit_margins": metrics.get("profit_margins", "N/A"),
            "revenue_growth_yoy": metrics.get("revenue_growth_yoy", "N/A"),
            "52_week_high": metrics.get("52_week_high", "N/A"),
            "52_week_low": metrics.get("52_week_low", "N/A"),
            "analyst_target_price": metrics.get("analyst_target_price", "N/A"),
            "analyst_rating": metrics.get("analyst_rating", "N/A"),
            "exchange": metrics.get("exchange", "Stock Exchange"),
            "sector": metrics.get("sector", "Technology & Services"),
            "industry": metrics.get("industry", "Enterprise Solutions"),
            "fiscal_calendar": metrics.get("fiscal_calendar", {}),
            "sec_officers": metrics.get("sec_officers", []),
            "temporal_year": 2026
        }

        if is_public:
            print(f"[Parent Agent] Classified as PUBLIC CORPORATION -> Ticker: {ticker} | Price: {metrics.get('current_price')} | Cap: {metrics.get('market_cap')}")
            emit("Research Supervisor", "Parent Director", "classified", f"Verified PUBLIC CORPORATION -> Ticker: {ticker} | Price: {metrics.get('current_price')} | Cap: {metrics.get('market_cap')}")
        else:
            print(f"[Parent Agent] Classified as PRIVATE ENTERPRISE -> Status: Unlisted (No public stock ticker)")
            emit("Research Supervisor", "Parent Director", "classified", f"Verified PRIVATELY HELD ENTERPRISE -> Status: Unlisted (No public stock ticker)")
        
        # Step 2: Parallel Subagent Execution with Locked Shared State
        print(f"---> [Concurrent Subagent Execution] Calling Financial Analyst, News Scout, and Corporate Biographer in parallel with Locked Shared State...")
        emit("Research Supervisor", "Parent Director", "dispatching", "Launching 3 specialized subagents in parallel with Locked Single Source of Truth...")

        emit("Financial Analyst Agent", "Financial Analyst", "running", "Evaluating canonical valuation matrix, price multiples, and margin dynamics...")
        emit("News Scout Agent", "News Scout", "running", "Scouring Google News RSS feeds for real-time market catalysts and sentiment...")
        emit("Corporate Biographer Agent", "Corporate Biographer", "running", "Querying corporate records and historical filings with 2026 temporal awareness...")

        with ThreadPoolExecutor(max_workers=3) as executor:
            f_fin = executor.submit(self.financial_agent.analyze, clean_target, shared_state)
            f_news = executor.submit(self.news_agent.analyze, clean_target, ticker, shared_state)
            f_bio = executor.submit(self.biography_agent.analyze, clean_target, shared_state)
            
            futures_map = {
                f_fin: ("Financial Analyst Agent", "Financial Analyst"),
                f_news: ("News Scout Agent", "News Scout"),
                f_bio: ("Corporate Biographer Agent", "Corporate Biographer")
            }

            for future in as_completed(futures_map):
                agent_name, role_name = futures_map[future]
                emit(agent_name, role_name, "completed", f"{role_name} completed analysis and returned validated intelligence.")

            fin_data = f_fin.result()
            news_data = f_news.result()
            bio_data = f_bio.result()

        # Step 3: Dynamic Multi-Agent Intelligence Synthesis & Strict Role-Binding Reconciliation
        entity_profile = bio_data.get("entity_profile", {})
        detected_events = news_data.get("detected_events", {})
        sentiment_pulse = news_data.get("sentiment_pulse", {
            "tone": "Balanced / Observant",
            "polarity": "neutral",
            "rationale": "Media coverage reflects active operational monitoring."
        })

        founding_info = entity_profile.get("founding_info", "")
        verified_acquisitions = entity_profile.get("verified_acquisitions", [])
        verified_segments = entity_profile.get("verified_segments", [])

        # Combine governance & regulatory events from both entity_profile and live News Scout
        breaking_gov = list(dict.fromkeys(
            (entity_profile.get("breaking_governance") or []) +
            (detected_events.get("governance_events") or [])
        ))
        breaking_reg = list(dict.fromkeys(
            (entity_profile.get("breaking_regulatory") or []) +
            (detected_events.get("regulatory_risks") or [])
        ))

        # Reconcile officers strictly across SEC/Yahoo, Wikipedia/Registry, and breaking governance disclosures
        officer_candidates: List[VerifiedOfficer] = []
        for raw_off in (entity_profile.get("active_officers") or []):
            try:
                officer_candidates.append(VerifiedOfficer(**raw_off))
            except Exception:
                pass
        if not officer_candidates:
            for raw_str in (entity_profile.get("verified_leadership") or []):
                parsed = parse_officer_string(raw_str, source="Verified Profile", priority=2)
                if parsed:
                    officer_candidates.append(parsed)
        for sec_off in (shared_state.get("sec_officers") or []):
            try:
                officer_candidates.append(VerifiedOfficer(**sec_off))
            except Exception:
                pass

        reconciled_officers = reconcile_officers(officer_candidates, breaking_governance=breaking_gov)
        verified_leadership = [o.formatted() for o in reconciled_officers]

        shared_state["founding_info"] = founding_info
        shared_state["active_officers"] = [o.model_dump() for o in reconciled_officers]
        shared_state["verified_leadership"] = verified_leadership
        shared_state["verified_acquisitions"] = verified_acquisitions
        shared_state["verified_segments"] = verified_segments
        shared_state["breaking_governance"] = breaking_gov
        shared_state["breaking_regulatory"] = breaking_reg
        shared_state["sentiment_pulse"] = sentiment_pulse

        print(f"\n[Parent Agent: {self.name}] Synthesizing multi-agent intelligence streams...")
        cfg = config.get_config()
        emit("Research Supervisor", "Parent Director", "synthesizing", f"Synthesizing comprehensive executive briefing & strategic outlook via {cfg['PROVIDER'].upper()} LLM...")
        
        scale_desc = metrics.get('revenue_scale_descriptor', 'Commercial Scale')
        peg_context = metrics.get('peg_rationale', '')
        fiscal_cal = shared_state.get("fiscal_calendar") or {}
        fiscal_summary = fiscal_cal.get("quarter_mapping_summary", "Standard calendar fiscal year.")
        recent_q = fiscal_cal.get("most_recent_reported_quarter", "")
        sentiment_tone = sentiment_pulse.get("tone", "Balanced / Observant")
        sentiment_rationale = sentiment_pulse.get("rationale", "")

        synthesis_prompt = f"""As Research Director, produce an in-depth, structured Executive Synthesis for {company_name} (Public Entity: {is_public}).

VERIFIED STATE (SINGLE SOURCE OF TRUTH):
- Company: {company_name} ({ticker}) | Exchange: {metrics.get('exchange', 'Stock Exchange')}
- Current Stock Price: {metrics.get('current_price', 'N/A')}
- Market Capitalization: {metrics.get('market_cap', 'N/A')}
- Trailing P/E: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))} | Forward P/E: {metrics.get('forward_pe', 'N/A')} | PEG Ratio: {metrics.get('peg_ratio', 'N/A')}
- TTM Revenue (Trailing 12 Months): {metrics.get('total_revenue', 'N/A')} ({scale_desc}; do NOT confuse with annual FY filings)
- Operating Margin: {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))} | Profit Margin: {metrics.get('profit_margins', 'N/A')}
- Fiscal Calendar Grounding: {fiscal_summary}

DYNAMIC CORPORATE PROFILE & REAL-TIME CATALYSTS:
- Founding & Origins: {founding_info if founding_info else 'Documented corporate founding'}
- Verified Active Leadership & Officers (STRICTLY BOUND): {", ".join(verified_leadership) if verified_leadership else 'Documented executive leadership'}
- Breaking Governance Shifts: {"; ".join(breaking_gov) if breaking_gov else 'Standard executive continuity'}
- Critical Regulatory Inquiries & Compliance: {"; ".join(breaking_reg) if breaking_reg else 'Standard regulatory trade compliance'}
- Official Reporting Segments & Products: {", ".join(verified_segments) if verified_segments else 'Documented core operating divisions'}
- Documented Strategic Acquisitions: {"; ".join(verified_acquisitions) if verified_acquisitions else 'Documented M&A filings'}
- Verified Media & Market Sentiment Pulse: {sentiment_tone} ({sentiment_rationale})
- PEG Valuation Rationale: {peg_context}

UNIVERSAL FACTUAL & CONTRADICTION PREVENTION DIRECTIVES:
1. Under NO circumstances state or quote a share price, multiple, or market cap that contradicts the Verified State above.
2. STRICT ROLE-BINDING: Name ONLY the Verified Active Leadership & Officers above. NEVER attribute the CEO title to executives of unrelated companies or former/resigned officers, and never invent an undocumented COO.
3. FISCAL QUARTER GROUNDING: Strictly use the company's fiscal quarter labels (most recent reported quarter: {recent_q if recent_q else 'latest fiscal period'}). Never confuse calendar quarters with non-calendar fiscal quarters.
4. SENTIMENT COHESION: Section 1 (Executive Summary) MUST match the Verified Media & Market Sentiment Pulse ({sentiment_tone}). NEVER describe sentiment as 'constructive' or 'bullish' if the verified media pulse is bearish, cautious, or mixed!
5. Business Architecture: Structure divisions strictly around the company's verified reporting units and products above.
6. Strategic Risks: Explicitly evaluate any breaking regulatory investigations, compliance scrutiny, or trade inquiries identified above.
7. FORMATTING & NEGATIVE CONSTRAINT: NEVER use LaTeX math delimiters ($...$, ^{{**}}, {{}}) around text or ratios (use $ ONLY for currency figures like $154.71). NEVER use meta-prompt terms like 'canonical', 'provided', 'supplied', or 'prompt'. Never repeat phrases like 'With a PEG ratio of X, PEG ratio of X'.
8. Do NOT leave any dangling headers or unfinished sentences.

Section 1: EXECUTIVE_SUMMARY
- Macro Enterprise Standing & Industry Positioning
- Core Commercial Drivers & Operational Scale
- Financial & Valuation Synthesis
- Sentiment & Event Integration (Aligned with {sentiment_tone})

Section 2: STRATEGIC_OUTLOOK
- Primary Long-Term Growth Vectors
- Technological & Moat Evolution
- Critical Risk Factors & Competitive Vulnerabilities (Include any detected regulatory or compliance scrutiny)

Subagent 1 (Financial Findings):
{fin_data.get('analysis', '')}

Subagent 2 (News & Events):
{news_data.get('analysis', '')}

Subagent 3 (Corporate Background & Moat):
{bio_data.get('analysis', '')}

Format strictly as:
EXECUTIVE_SUMMARY:
[Detailed text]
STRATEGIC_OUTLOOK:
[Detailed text]"""

        synthesis_text = self.generate_response(synthesis_prompt)
        
        exec_summary = ""
        strategic_outlook = ""
        
        if "EXECUTIVE_SUMMARY:" in synthesis_text and "STRATEGIC_OUTLOOK:" in synthesis_text:
            parts = synthesis_text.split("STRATEGIC_OUTLOOK:")
            exec_summary = parts[0].replace("EXECUTIVE_SUMMARY:", "").strip()
            strategic_outlook = parts[1].strip()
        else:
            # Dynamic fallback based on real facts, reconciled officers, and aligned sentiment tone
            if is_public:
                if breaking_gov and verified_leadership:
                    gov_str = f"In corporate governance, active leadership is currently stewarded by {', '.join(verified_leadership)}; key developments include: {'; '.join(breaking_gov)}."
                elif breaking_gov:
                    gov_str = f"In corporate governance, recent key developments include: {'; '.join(breaking_gov)}."
                elif verified_leadership:
                    gov_str = f"Executive leadership is stewarded by verified active officers: {', '.join(verified_leadership)}."
                else:
                    gov_str = ""

                peg_sentence = f"A {peg_context} " if peg_context else f"The equity trades at a PEG ratio of {metrics.get('peg_ratio', 'N/A')}. "
                sentiment_sentence = f"Institutional and media sentiment is currently {sentiment_tone.lower()}. {sentiment_rationale} "

                exec_summary = (
                    f"### Macro Standing & Corporate Scale\n"
                    f"{company_name} ({ticker}) stands as a prominent public enterprise operating within the {metrics.get('sector', 'Technology')} sector, "
                    f"traded on the {metrics.get('exchange', 'Stock Exchange')} with an aggregate market valuation of {metrics.get('market_cap', 'N/A')}. "
                    f"The organization commands an extensive commercial footprint, serving institutional and enterprise client bases across primary global markets.\n\n"
                    f"### Financial Architecture & Valuation Context\n"
                    f"From a fundamental valuation perspective, the equity trades at {metrics.get('current_price', 'N/A')} against a trailing P/E multiple of {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))} and a forward P/E of {metrics.get('forward_pe', 'N/A')}. "
                    f"{peg_sentence}"
                    f"Trading over the past 52 weeks spans {metrics.get('52_week_low', 'N/A')} to {metrics.get('52_week_high', 'N/A')}, supported by {scale_desc} TTM revenue volumes of {metrics.get('total_revenue', 'N/A')} and net margins of {metrics.get('profit_margins', 'N/A')}.\n\n"
                    f"### Commercial Execution & Market Sentiment\n"
                    f"{sentiment_sentence}"
                    f"{gov_str}"
                )
                
                reg_risk_str = f"\n\n### Regulatory, Legal & Geopolitical Scrutiny\nKey regulatory observation points include: {'; '.join(breaking_reg)}. The enterprise actively maintains compliance mechanisms to navigate international and trade requirements." if breaking_reg else (
                    "\n\n### Critical Risk Factors & Vulnerabilities\nPrimary operational and macro risks include foreign exchange volatility, competitive talent retention, potential enterprise IT budget rationalization, and evolving regulatory standards."
                )
                
                growth_segments = f"across core operating lines including {', '.join(verified_segments)}" if verified_segments else "through international expansion and higher-margin platform delivery"
                strategic_outlook = (
                    f"### Strategic Growth Vectors\n"
                    f"{company_name}'s multi-year expansion is propelled by aggressive technological innovation, scaling enterprise contracts {growth_segments}, "
                    f"and deepening integration across high-margin commercial ecosystems.{reg_risk_str}"
                )
            else:
                exec_summary = (
                    f"### Private Enterprise Standing & Core Scale\n"
                    f"{company_name} operates as a privately held commercial enterprise, unlisted on public stock exchanges and exempt from mandatory public SEC filings. "
                    f"The enterprise has established a targeted market presence by providing specialized domain solutions, enterprise engineering, and technological delivery.\n\n"
                    f"### Capital Structure & Growth Mechanics\n"
                    f"As a private entity, corporate capitalization is fueled through private venture funding, private equity partnerships, or self-sustaining commercial cash flow. "
                    f"Without the pressure of quarterly public earnings disclosures, the organization maintains operational agility to prioritize long-term platform development.\n\n"
                    f"### Market Engagement & Verified Execution\n"
                    f"Recent media monitoring highlights steady market execution, active client deployments, and technological capabilities in enterprise-scale architecture."
                )
                strategic_outlook = (
                    f"### Long-Term Value Drivers\n"
                    f"Strategic upside for {company_name} centers on deepening proprietary intellectual property, expanding strategic technology partnerships, and scaling annual contract value across tier-1 enterprise clients.\n\n"
                    f"### Key Operational Risks\n"
                    f"Primary risk considerations include private capital market liquidity conditions, competition from well-funded incumbents, and client concentration risks characteristic of privately held technology firms."
                )

        # Step 3: Final Compilation & Export
        elapsed_time = round(time.time() - start_time, 2)
        final_dossier = {
            "company_name": company_name,
            "ticker": ticker,
            "is_public": is_public,
            "metrics": metrics,
            "execution_time": elapsed_time,
            "executive_summary": exec_summary,
            "corporate_background": bio_data.get("analysis", ""),
            "financial_analysis": fin_data.get("analysis", ""),
            "recent_news_analysis": news_data.get("analysis", ""),
            "strategic_outlook": strategic_outlook,
            "news_articles": news_data.get("articles", []),
            "shared_state": shared_state
        }

        # Step 4: Run QA Critic Node to audit cross-agent consistency & typography
        emit("QA Critic Agent", "Quality Assurance & Fact-Checking", "verifying", "Auditing dossier for Single Source of Truth consistency, tabular verification, and typography sanitization...")
        final_dossier = self.qa_critic.review_and_sanitize(final_dossier, shared_state)

        # Generate In-Memory Report (No disk files created)
        emit("Publisher", "PDF & Dossier Publisher", "publishing", "Compiling publication-grade in-memory PDF dossier...")
        pdf_bytes = generate_pdf_report(final_dossier)
        
        emit("Research Supervisor", "Parent Director", "complete", f"Investigation completed successfully in {elapsed_time}s! All dossiers verified.")
        print(f"\n[Parent Agent: {self.name}] Investigation completed in {elapsed_time}s! (In-memory, 0 disk files created)")
        
        return {
            "dossier": final_dossier,
            "pdf_bytes": pdf_bytes,
            "execution_time": elapsed_time
        }

    def _write_markdown_report(self, dossier: Dict[str, Any], path: str):
        """Save an extensive, human-readable markdown file with explicit detailed sources heading."""
        metrics = dossier.get("metrics", {})
        is_public = dossier.get("is_public", True)
        
        md_content = f"""# Autonomous Market Intelligence Dossier: {dossier['company_name']}
*Generated by Autonomous Parent Orchestrator and Specialized Subagents*

---

## 1. Executive Summary & Strategic Synthesis
{dossier['executive_summary']}

---
"""
        if is_public:
            md_content += f"""## 2. Fundamental Valuation & Financial Snapshot (Public Equity)
| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| **Current Stock Price** | {metrics.get('current_price', 'N/A')} | **Market Capitalization** | {metrics.get('market_cap', 'N/A')} |
| **P/E Ratio** | {metrics.get('pe_ratio', 'N/A')} | **Total Revenue** | {metrics.get('total_revenue', 'N/A')} |
| **52-Week Range** | {metrics.get('52_week_low', 'N/A')} - {metrics.get('52_week_high', 'N/A')} | **Profit Margin** | {metrics.get('profit_margins', 'N/A')} |
| **Analyst Target Price** | {metrics.get('analyst_target_price', 'N/A')} | **Consensus Rating** | {metrics.get('analyst_rating', 'N/A')} |

### Detailed Financial & Valuation Analysis
{dossier.get('financial_analysis', '')}
"""
        else:
            md_content += f"""## 2. Corporate Structure & Private Enterprise Profile
| Dimension | Corporate Status | Dimension | Corporate Status |
| :--- | :--- | :--- | :--- |
| **Entity Classification** | Privately Held Enterprise | **Exchange Listing** | Unlisted (No Public Ticker) |
| **Ownership Structure** | Private / Venture / Founder | **Regulatory Filing** | Exempt from SEC 10-K Filings |
| **Capital Basis** | Private Equity / Retained Earnings | **Market Access** | Secondary / Private Direct |

### Detailed Financial & Capital Structure Analysis
{dossier.get('financial_analysis', '')}
"""

        md_content += f"""
---

## 3. Corporate Background, Core Operations & Moat
{dossier['corporate_background']}

---

## 4. Recent News, Strategic Moves & Market Sentiment
{dossier['recent_news_analysis']}

---

### Here are the Detailed Sources:
"""
        articles = dossier.get("news_articles", [])
        if articles:
            for item in articles:
                md_content += f"- **[{item.get('title')}]({item.get('url')})**\n  *Source*: {item.get('source')} | *Date*: {item.get('date')} | *Link*: {item.get('url')}\n"
        else:
            md_content += "- *No recent breaking news headlines identified for this entity.*\n"

        md_content += f"""
---

## 5. Strategic Outlook, Growth Vectors & Key Risks
{dossier['strategic_outlook']}

---
*Report automatically compiled and validated using 100% Free Open-Source Multi-Agent Architecture.*
"""
        if path:
            import os
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md_content)
        return md_content
