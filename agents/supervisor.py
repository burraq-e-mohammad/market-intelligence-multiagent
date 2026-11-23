from agents.base_agent import BaseAgent
from agents.entity_resolver import EntityResolverAgent
from agents.financial_agent import FinancialAnalystAgent
from agents.news_agent import NewsScoutAgent
from agents.biography_agent import BiographyAgent
from agents.qa_validator_agent import QualityAssuranceAgent
from tools.finance_tool import get_financial_metrics
from tools.wiki_tool import get_company_biography
from tools.pdf_tool import generate_pdf_report
from tools.intelligence_tool import calculate_health_scores, get_competitor_comparison, generate_executive_memo
from tools.schemas import VerifiedOfficer, ResolvedEntity, parse_officer_string, reconcile_officers
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
        
        self.entity_resolver = EntityResolverAgent()
        self.financial_agent = FinancialAnalystAgent()
        self.news_agent = NewsScoutAgent()
        self.biography_agent = BiographyAgent()
        self.quality_assurance = QualityAssuranceAgent()

    def run_investigation(
        self,
        target_input: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        region_hint: Optional[str] = None,
        industry_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full hierarchical multi-agent workflow:
        0. Pre-flight EntityResolverAgent disambiguates short/ambiguous/regional entities into a strict ResolvedEntity.
        1. Financial feed + anchored Corporate Biography populate locked Shared State.
        2. Subagents run concurrently in parallel via ThreadPoolExecutor.
        3. Parent Agent synthesizes data into deep Executive Briefing & Strategic Outlook.
        4. QA Critic audits & sanitizes; Publisher compiles in-memory PDF dossier.
        """
        start_time = time.time()
        clean_target = target_input.strip()
        progress_state = {"pct": 0}

        def emit(agent: str, role: str, status: str, message: str, progress: Optional[int] = None, progress_cap: Optional[int] = None):
            elapsed = round(time.time() - start_time, 1)
            if progress is not None:
                progress_state["pct"] = max(progress_state["pct"], min(100, int(progress)))
            event = {
                "time": elapsed,
                "agent": agent,
                "role": role,
                "status": status,
                "message": message,
                "progress": progress_state["pct"],
                "progress_cap": progress_cap if progress_cap is not None else min(99, progress_state["pct"] + 4)
            }
            if progress_callback:
                try:
                    progress_callback(event)
                except Exception:
                    pass

        emit("Research Supervisor", "Parent Director", "started", f"Initiating deep investigation project for '{clean_target}'...", progress=5, progress_cap=9)
        print(f"\n[Parent Agent: {self.name}] Initiating research project for '{clean_target}'...")

        # Step 0: Pre-Flight Entity Disambiguation (prevents 'Jazz' -> JAZZ Pharma/NBA, 'Zong' -> 1781 ship, 'Samsung' -> Chaebol)
        emit("Entity Resolver Agent", "Pre-Flight Disambiguation", "resolving", f"Disambiguating target entity, ownership tier, and search anchors for '{clean_target}'...", progress=10, progress_cap=19)
        pre_resolved = self.entity_resolver.resolve(clean_target, region_hint=region_hint, industry_hint=industry_hint)

        # Step 1: Route Financial Feed by Pre-Flight Entity Classification (PUBLIC | SUBSIDIARY | PRIVATE)
        if pre_resolved.entity_type == "SUBSIDIARY":
            is_public = False
            entity_type = "SUBSIDIARY"
            company_name = pre_resolved.canonical_name
            ticker = f"SUBSIDIARY ({pre_resolved.parent_ticker})" if pre_resolved.parent_ticker else "WHOLLY-OWNED SUBSIDIARY"
            parent_metrics = {}
            if pre_resolved.parent_ticker:
                try:
                    parent_fin = get_financial_metrics(pre_resolved.parent_ticker)
                    if parent_fin.get("is_public"):
                        parent_metrics = parent_fin.get("data", {})
                except Exception:
                    pass
            metrics = {
                "symbol": ticker,
                "company_name": company_name,
                "legal_entity_name": pre_resolved.legal_entity_name,
                "entity_type": "Wholly-Owned Operating Subsidiary",
                "exchange": f"Unlisted Subsidiary (Parent: {pre_resolved.parent_company})",
                "sector": pre_resolved.sector,
                "industry": pre_resolved.sector,
                "headquarters": pre_resolved.headquarters,
                "parent_company": pre_resolved.parent_company,
                "parent_ticker": pre_resolved.parent_ticker,
                "ownership_pct": pre_resolved.ownership_pct,
                "local_currency": pre_resolved.local_currency,
                "subsidiary_kpis": pre_resolved.subsidiary_kpis,
                "parent_metrics": parent_metrics,
                "is_public": False
            }
            resolved = pre_resolved
        else:
            fin_query = pre_resolved.ticker if (pre_resolved.entity_type == "PUBLIC" and pre_resolved.ticker) else clean_target
            tool_fin = get_financial_metrics(fin_query)
            is_public = tool_fin.get("is_public", False)
            metrics = tool_fin.get("data", {})
            # Reconcile ResolvedEntity with live financial probe if not already a curated entity
            if pre_resolved.entity_type == "PUBLIC" and pre_resolved.ticker:
                resolved = pre_resolved
                company_name = pre_resolved.canonical_name or metrics.get("company_name", clean_target)
            else:
                resolved = self.entity_resolver.resolve(
                    clean_target,
                    region_hint=region_hint,
                    industry_hint=industry_hint,
                    financial_probe=tool_fin
                )
                company_name = metrics.get("company_name", resolved.canonical_name)
            entity_type = resolved.entity_type
            ticker = metrics.get("symbol", resolved.ticker or "PRIVATE / UNLISTED")

        resolved_dict = resolved.model_dump()
        emit("Entity Resolver Agent", "Pre-Flight Disambiguation", "completed", f"Resolved '{clean_target}' -> {resolved.canonical_name} [{entity_type}] | Wiki: {resolved.wikipedia_title}", progress=20, progress_cap=25)

        # Fetch Corporate Biography strictly anchored to ResolvedEntity (exact wikipedia_title + negative keyword guards + live business_summary fallback)
        emit("Corporate Biographer Agent", "Corporate Biographer", "fetching_bio", f"Fetching anchored corporate profile and executive roster for {resolved.canonical_name}...", progress=26, progress_cap=31)
        bio_target = resolved.canonical_name if entity_type == "SUBSIDIARY" else (company_name if (is_public and company_name and len(company_name) > len(clean_target)) else clean_target)
        tool_bio = get_company_biography(
            bio_target,
            resolved_entity=resolved_dict,
            business_summary=metrics.get("business_summary", "")
        )

        pre_profile = tool_bio.get("entity_profile", {})
        infobox_identity = pre_profile.get("infobox_identity") or {}
        if infobox_identity:
            resolved_dict = resolved.model_dump()
            if infobox_identity.get("legal_entity_name"):
                resolved_dict["legal_entity_name"] = infobox_identity["legal_entity_name"]
            if infobox_identity.get("parent_company"):
                resolved_dict["parent_company"] = infobox_identity["parent_company"]
            if infobox_identity.get("headquarters"):
                resolved_dict["headquarters"] = infobox_identity["headquarters"]
            resolved = ResolvedEntity(**resolved_dict)
        if pre_profile.get("headquarters"):
            resolved_dict = resolved.model_dump()
            resolved_dict["headquarters"] = pre_profile["headquarters"]
            resolved = ResolvedEntity(**resolved_dict)
        else:
            resolved_dict = resolved.model_dump()
        pre_breaking_gov = pre_profile.get("breaking_governance", [])
        pre_breaking_reg = pre_profile.get("breaking_regulatory", [])

        pre_officer_cands: List[VerifiedOfficer] = []
        for raw_off in (pre_profile.get("active_officers") or []):
            try:
                pre_officer_cands.append(VerifiedOfficer(**raw_off))
            except Exception:
                pass
        if not pre_officer_cands:
            for raw_str in (pre_profile.get("verified_leadership") or []):
                parsed = parse_officer_string(raw_str, source="Verified Profile", priority=2)
                if parsed:
                    pre_officer_cands.append(parsed)
        # Only fall back to Yahoo/SEC companyOfficers when no current Infobox/Registry roster exists
        if not pre_officer_cands and entity_type == "PUBLIC":
            for sec_off in (metrics.get("sec_officers") or []):
                try:
                    pre_officer_cands.append(VerifiedOfficer(**sec_off))
                except Exception:
                    pass
        pre_reconciled = reconcile_officers(pre_officer_cands, breaking_governance=pre_breaking_gov)

        shared_state = {
            "company_name": company_name,
            "ticker": ticker,
            "is_public": is_public,
            "entity_type": entity_type,
            "resolved_entity": resolved_dict,
            "metrics": metrics,
            "current_price": metrics.get("current_price", "N/A"),
            "extended_hours_context": metrics.get("extended_hours_context", ""),
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
            "sector": metrics.get("sector", resolved.sector),
            "industry": metrics.get("industry", resolved.sector),
            "fiscal_calendar": metrics.get("fiscal_calendar", {}),
            "sec_officers": metrics.get("sec_officers", []),
            "verified_leadership": [o.formatted() for o in pre_reconciled],
            "breaking_governance": pre_breaking_gov,
            "breaking_regulatory": pre_breaking_reg,
            "private_financials": pre_profile.get("private_financials", {}),
            "bio_tool_result": tool_bio,
            "temporal_year": 2026
        }

        if entity_type == "PUBLIC":
            print(f"[Parent Agent] Classified as PUBLIC CORPORATION -> Ticker: {ticker} | Price: {metrics.get('current_price')} | Cap: {metrics.get('market_cap')}")
            emit("Research Supervisor", "Parent Director", "classified", f"Verified PUBLIC CORPORATION -> Ticker: {ticker} | Price: {metrics.get('current_price')} | Cap: {metrics.get('market_cap')}", progress=32, progress_cap=35)
        elif entity_type == "SUBSIDIARY":
            print(f"[Parent Agent] Classified as WHOLLY-OWNED SUBSIDIARY -> {company_name} | Parent: {resolved.parent_company}")
            emit("Research Supervisor", "Parent Director", "classified", f"Verified WHOLLY-OWNED SUBSIDIARY -> Parent: {resolved.parent_company} | HQ: {resolved.headquarters}", progress=32, progress_cap=35)
        else:
            print(f"[Parent Agent] Classified as PRIVATE ENTERPRISE -> Status: Unlisted (No public stock ticker)")
            emit("Research Supervisor", "Parent Director", "classified", f"Verified PRIVATELY HELD ENTERPRISE -> Status: Unlisted (No public stock ticker)", progress=32, progress_cap=35)
        
        # Step 2: Parallel Subagent Execution with Locked Shared State
        print(f"---> [Concurrent Subagent Execution] Calling Financial Analyst, News Scout, and Corporate Biographer in parallel with Locked Shared State...")
        emit("Research Supervisor", "Parent Director", "dispatching", "Launching 3 specialized subagents in parallel with Locked Single Source of Truth...", progress=36, progress_cap=49)

        emit("Financial Analyst Agent", "Financial Analyst", "running", "Evaluating canonical valuation matrix, price multiples, and margin dynamics...", progress=38, progress_cap=49)
        emit("News Scout Agent", "News Scout", "running", "Scouring Google News RSS feeds for real-time market catalysts and sentiment...", progress=38, progress_cap=49)
        emit("Corporate Biographer Agent", "Corporate Biographer", "running", "Querying corporate records and historical filings with 2026 temporal awareness...", progress=38, progress_cap=49)

        with ThreadPoolExecutor(max_workers=3) as executor:
            f_fin = executor.submit(self.financial_agent.analyze, clean_target, shared_state)
            f_news = executor.submit(self.news_agent.analyze, clean_target, ticker, shared_state)
            f_bio = executor.submit(self.biography_agent.analyze, bio_target, shared_state)
            
            futures_map = {
                f_fin: ("Financial Analyst Agent", "Financial Analyst"),
                f_news: ("News Scout Agent", "News Scout"),
                f_bio: ("Corporate Biographer Agent", "Corporate Biographer")
            }

            completed_subagents = 0
            subagent_milestones = [(50, 61), (62, 73), (74, 77)]
            for future in as_completed(futures_map):
                agent_name, role_name = futures_map[future]
                pct, cap = subagent_milestones[min(completed_subagents, len(subagent_milestones) - 1)]
                completed_subagents += 1
                emit(
                    agent_name,
                    role_name,
                    "completed",
                    f"{role_name} completed analysis ({completed_subagents}/3 subagents done).",
                    progress=pct,
                    progress_cap=cap
                )

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
        if not officer_candidates:
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
        emit("Research Supervisor", "Parent Director", "synthesizing", f"Synthesizing comprehensive executive briefing & strategic outlook via {cfg['PROVIDER'].upper()} LLM...", progress=78, progress_cap=87)
        
        scale_desc = metrics.get('revenue_scale_descriptor', 'Commercial Scale')
        peg_context = metrics.get('peg_rationale', '')
        fiscal_cal = shared_state.get("fiscal_calendar") or {}
        fiscal_summary = fiscal_cal.get("quarter_mapping_summary", "Standard calendar fiscal year.")
        recent_q = fiscal_cal.get("most_recent_reported_quarter", "")
        sentiment_tone = sentiment_pulse.get("tone", "Balanced / Observant")
        sentiment_rationale = sentiment_pulse.get("rationale", "")
        pf = shared_state.get("private_financials") or {}

        if entity_type == "PUBLIC" and is_public:
            verified_state_block = f"""VERIFIED PUBLIC-EQUITY STATE (SINGLE SOURCE OF TRUTH):
- Company: {company_name} ({ticker}) | Exchange: {metrics.get('exchange', 'Stock Exchange')}
- Current Stock Price: {metrics.get('current_price', 'N/A')}
- Extended-Hours Context: {metrics.get('extended_hours_context', 'Regular session close')}
- Market Capitalization: {metrics.get('market_cap', 'N/A')}
- Trailing P/E: {metrics.get('trailing_pe', metrics.get('pe_ratio', 'N/A'))} | Forward P/E: {metrics.get('forward_pe', 'N/A')} | PEG Ratio: {metrics.get('peg_ratio', 'N/A')}
- TTM Revenue (Trailing 12 Months): {metrics.get('total_revenue', 'N/A')} ({scale_desc}; do NOT confuse with annual FY filings)
- Operating Margin: {metrics.get('operating_margins', metrics.get('profit_margins', 'N/A'))} | Profit Margin: {metrics.get('profit_margins', 'N/A')}
- PEG Valuation Rationale: {peg_context}
- Fiscal Calendar Grounding: {fiscal_summary}"""
            entity_fin_rule = (
                "1. PUBLIC EQUITY ACCURACY: Under NO circumstances state or quote a regular-session share price, multiple, or market cap that contradicts the Verified State above. "
                "If extended-hours trading or fresh post-earnings actuals appear in Subagent 2 (News & Events), explicitly highlight those concrete figures (revenue, EPS, guidance, after-hours move) and note that market-data TTM feeds roll forward over 24-72 hours."
            )
            fin_section_label = "Public Equity Multiples"
        elif entity_type == "SUBSIDIARY":
            sub_kpis = resolved_dict.get("subsidiary_kpis") or {}
            parent_co = resolved_dict.get("parent_company") or "Parent Holding Group"
            ownership = resolved_dict.get("ownership_pct") or f"Wholly-owned subsidiary of {parent_co}"
            currency = resolved_dict.get("local_currency") or "Local Currency"
            verified_state_block = f"""VERIFIED WHOLLY-OWNED SUBSIDIARY STATE (CONSOLIDATED ENTITY):
- Canonical Name: {company_name} | Legal Name: {resolved_dict.get('legal_entity_name')}
- Ownership Structure: {ownership}
- Headquarters & Sector: {resolved_dict.get('headquarters')} | {resolved_dict.get('sector')}
- Functional Currency: {currency} | Reporting Basis: {sub_kpis.get('reporting_basis', f'Consolidated under {parent_co}')}
- Reported Revenue ({currency}): {sub_kpis.get('annual_revenue', f'Undisclosed standalone (Consolidated under {parent_co})')}
- Reported EBITDA ({currency}): {sub_kpis.get('ebitda', f'Undisclosed standalone (Consolidated under {parent_co})')}
- Operational & Subscriber KPIs: {sub_kpis.get('subscribers', 'Regional market operator')}
- Digital / Platform Ecosystem: {sub_kpis.get('digital_ecosystem', 'Core commercial infrastructure')}
- Credit Rating & Backing: {sub_kpis.get('credit_rating', f'Backed by {parent_co}')}"""
            entity_fin_rule = (
                f"1. STRICT SUBSIDIARY ROUTING: This is a WHOLLY-OWNED OPERATING SUBSIDIARY ({ownership}). "
                f"NEVER mention 'venture capital rounds', 'founder equity', generic 'B2B SaaS recurring software contracts', or standalone public stock P/E & PEG multiples! "
                f"Explicitly anchor the analysis in parent ownership ({parent_co}), local-currency ({currency}) revenue/EBITDA or consolidation status, subscriber scale, and regulatory/FX dynamics."
            )
            fin_section_label = f"Parent Ownership, {currency} Scale & Operational KPIs"
        else:
            pf_vals = " | ".join(pf.get("valuations", [])) or "Private institutional financing rounds"
            pf_funds = " | ".join(pf.get("funding_rounds", [])) or "Venture & strategic private capital"
            pf_revs = " | ".join(pf.get("revenue_and_arr", [])) or "Private ARR / contract revenue disclosures"
            pf_ipo = " | ".join(pf.get("burn_and_ipo", [])) or "Unlisted private corporate structure"
            verified_state_block = f"""VERIFIED PRIVATE-ENTERPRISE STATE (UNLISTED ENTITY):
- Company: {company_name} | Status: PRIVATELY HELD / UNLISTED (Exempt from SEC Form 10-K)
- Latest Post-Money Valuation Context: {pf_vals}
- Documented Capital Raises & Backers: {pf_funds}
- Documented Revenue & ARR Trajectory: {pf_revs}
- Cash Burn, Restructuring & IPO Roadmap: {pf_ipo}"""
            entity_fin_rule = (
                "1. STRICT PRIVATE-ENTITY ROUTING: This is a PRIVATELY HELD enterprise with NO public stock ticker, NO Forward P/E, and NO PEG ratio. "
                "NEVER output public-equity P/E or PEG ratio boilerplate, and NEVER describe revenue under $100B as 'triple-digit billion' "
                "($10B-$99.9B is double-digit billion; $1B-$9.9B is multi-billion). Highlight documented post-money valuations, funding rounds, ARR run rate, and IPO timeline."
            )
            fin_section_label = "Private Valuation, Funding & ARR"

        synthesis_prompt = f"""As Research Director, produce an in-depth, structured Executive Synthesis for {company_name} (Entity Classification: {entity_type}).

{verified_state_block}

DYNAMIC CORPORATE PROFILE & REAL-TIME CATALYSTS:
- Founding & Origins: {founding_info if founding_info else 'Documented corporate founding'}
- Verified Active Leadership & Officers (STRICTLY BOUND): {", ".join(verified_leadership) if verified_leadership else 'Documented executive leadership'}
- Breaking Governance Shifts: {"; ".join(breaking_gov) if breaking_gov else 'Standard executive continuity'}
- Critical Regulatory Inquiries & Compliance: {"; ".join(breaking_reg) if breaking_reg else 'Standard regulatory trade compliance'}
- Official Reporting Segments & Products: {", ".join(verified_segments) if verified_segments else 'Documented core operating divisions'}
- Documented Strategic Acquisitions: {"; ".join(verified_acquisitions) if verified_acquisitions else 'Documented M&A filings'}
- Verified Media & Market Sentiment Pulse: {sentiment_tone} ({sentiment_rationale})

UNIVERSAL FACTUAL & CONTRADICTION PREVENTION DIRECTIVES:
{entity_fin_rule}
2. STRICT ROLE-BINDING: Name ONLY the Verified Active Leadership & Officers above. NEVER attribute the CEO title to executives of unrelated companies or former/resigned officers, and never invent an undocumented COO.
3. FISCAL QUARTER GROUNDING: Strictly use accurate calendar/fiscal periods ({recent_q if (is_public and recent_q) else 'current 2026 operating period'}).
4. SENTIMENT COHESION: Section 1 (Executive Summary) MUST match the Verified Media & Market Sentiment Pulse ({sentiment_tone}). NEVER describe sentiment as 'constructive' or 'bullish' if the verified media pulse is bearish, cautious, or mixed!
5. Business Architecture: Structure divisions strictly around the company's verified reporting units and products above.
6. Strategic Risks: Explicitly evaluate any breaking regulatory investigations, compliance scrutiny, or trade inquiries identified above.
7. FORMATTING & NEGATIVE CONSTRAINT: NEVER escape dollar signs with backslashes (write $852 billion or $3.75T, NEVER \\$852 billion). NEVER use LaTeX math delimiters ($...$, ^{{**}}, {{}}) around text or ratios. NEVER use meta-prompt terms like 'canonical', 'provided', 'supplied', or 'prompt'.
8. Do NOT leave any dangling headers or unfinished sentences.

Section 1: EXECUTIVE_SUMMARY
- Macro Enterprise Standing & Industry Positioning
- Core Commercial Drivers & Operational Scale
- Financial & Valuation Synthesis ({fin_section_label})
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

        emit("Research Supervisor", "Parent Director", "synthesizing", "Waiting at most 18 seconds for the executive synthesis provider...", progress=82, progress_cap=87)
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
                clean_gov_join = "; ".join(g.rstrip(". ") for g in breaking_gov)
                if breaking_gov and verified_leadership:
                    gov_str = f"In corporate governance, active leadership is currently stewarded by {', '.join(verified_leadership)}; key developments include: {clean_gov_join}."
                elif breaking_gov:
                    gov_str = f"In corporate governance, recent key developments include: {clean_gov_join}."
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
                
                clean_reg_join = "; ".join(r.rstrip(". ") for r in breaking_reg)
                reg_risk_str = f"\n\n### Regulatory, Legal & Geopolitical Scrutiny\nKey regulatory observation points include: {clean_reg_join}. The enterprise actively maintains compliance mechanisms to navigate international and trade requirements." if breaking_reg else (
                    "\n\n### Critical Risk Factors & Vulnerabilities\nPrimary risks include company-specific demand cyclicality, supply-chain execution, foreign exchange exposure, regulatory compliance, and competitive pressure."
                )
                
                growth_segments = f"across core operating lines including {', '.join(verified_segments)}" if verified_segments else "through international expansion and higher-margin platform delivery"
                strategic_outlook = (
                    f"### Strategic Growth Vectors\n"
                    f"{company_name}'s multi-year expansion is propelled by aggressive technological innovation, scaling enterprise contracts {growth_segments}, "
                    f"and deepening integration across high-margin commercial ecosystems.{reg_risk_str}"
                )
            elif entity_type == "SUBSIDIARY":
                sub_kpis = resolved_dict.get("subsidiary_kpis") or {}
                parent_co = resolved_dict.get("parent_company") or "Not verified"
                ownership = resolved_dict.get("ownership_pct") or "Ownership structure not verified"
                currency = resolved_dict.get("local_currency") or "Not disclosed"
                clean_reg_join = "; ".join(r.rstrip(". ") for r in breaking_reg)
                reg_str = f"\n\n### Regulatory, Spectrum & Macroeconomic Risks\nKey regulatory and operating risks include: {clean_reg_join}." if breaking_reg else (
                    f"\n\n### Key Operational & Macroeconomic Risks\nDo not invent subsidiary-specific risks. State only risks supported by the Verified State or live source findings."
                )

                exec_summary = (
                    f"### Subsidiary Standing & Parent Ownership\n"
                    f"{company_name} (legal entity: {resolved_dict.get('legal_entity_name') or 'Not verified'}) has headquarters status of {resolved_dict.get('headquarters') or 'Not verified'} and ownership status of {ownership}. "
                    f"Verified sector: {resolved_dict.get('sector') or 'Not verified'}.\n\n"
                    f"### Consolidated Financial Scale & Operational KPIs ({currency})\n"
                    f"Financials are reported under {sub_kpis.get('reporting_basis', parent_co)}. "
                    f"Documented local-currency figures show Revenue of {sub_kpis.get('annual_revenue', f'Undisclosed standalone (Consolidated under {parent_co})')} and EBITDA of {sub_kpis.get('ebitda', f'Undisclosed standalone (Consolidated under {parent_co})')}. "
                    f"Documented subscriber scale: {sub_kpis.get('subscribers', 'Not disclosed')}. Digital/platform details: {sub_kpis.get('digital_ecosystem', 'Not disclosed')}.\n\n"
                    f"### Market Sentiment & Strategic Positioning\n"
                    f"Current media and market sentiment is {sentiment_tone.lower()}. Credit and capital backing remain anchored by {sub_kpis.get('credit_rating', parent_co)}."
                )
                growth_segments = f"across {', '.join(verified_segments)}" if verified_segments else "only as supported by verified public disclosures"
                strategic_outlook = (
                    f"### Strategic Growth Vectors\n"
                    f"{company_name}'s forward trajectory must be limited to verified operating disclosures {growth_segments}.{reg_str}"
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
            "entity_type": entity_type,
            "resolved_entity": resolved_dict,
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

        # Step 3b: Attach deterministic intelligence assets (Health Scorecard, Peer Benchmark, Bull vs. Bear Memo)
        final_dossier["health_scorecard"] = calculate_health_scores(final_dossier)
        final_dossier["competitor_comparison"] = get_competitor_comparison(final_dossier)
        final_dossier["executive_memo"] = generate_executive_memo(final_dossier)

        # Step 4: Run QA Critic Node to audit cross-agent consistency & typography
        emit("QA Critic Agent", "Quality Assurance & Fact-Checking", "verifying", "Auditing dossier for Single Source of Truth consistency, tabular verification, and typography sanitization...", progress=88, progress_cap=93)
        final_dossier = self.quality_assurance.review_and_sanitize(final_dossier, shared_state)

        # Generate In-Memory Report (No disk files created)
        emit("Publisher", "PDF & Dossier Publisher", "publishing", "Compiling publication-grade in-memory PDF dossier...", progress=94, progress_cap=98)
        pdf_bytes = generate_pdf_report(final_dossier)
        elapsed_time = round(time.time() - start_time, 2)
        
        if not isinstance(pdf_bytes, (bytes, bytearray)) or len(pdf_bytes) < 100:
            emit("Publisher", "PDF & Dossier Publisher", "error", "PDF publication failed; no downloadable report was generated.", progress=98, progress_cap=99)
            raise RuntimeError("PDF publication failed")

        emit("Research Supervisor", "Parent Director", "complete", f"Investigation completed successfully in {elapsed_time}s! PDF and dossier ready.", progress=100, progress_cap=100)
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
