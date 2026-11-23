import sys
import os

# Auto-mount local project root & virtual environment site-packages so the app runs cleanly
# even when launched via global `streamlit run frontend/app.py` outside an activated venv.
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site_candidates = [
    os.path.join(_root, "venv", "Lib", "site-packages"),
    os.path.join(_root, ".venv", "Lib", "site-packages"),
    os.path.join(_root, "venv", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
]
for _sp in _venv_site_candidates:
    if os.path.isdir(_sp) and _sp not in sys.path:
        sys.path.insert(0, _sp)

import streamlit as st
import requests
import json
import time
import html
import queue
import threading

def _get_stretch_kw():
    """
    Returns {'width': 'stretch'} on modern Streamlit versions to eliminate deprecation warnings,
    or falls back to {'use_container_width': True} on older versions.
    """
    try:
        import inspect
        if "width" in inspect.signature(st.button).parameters:
            return {"width": "stretch"}
    except Exception:
        pass
    return {"use_container_width": True}

STRETCH_KW = _get_stretch_kw()

# Page Config
st.set_page_config(
    page_title="Autonomous Market Intelligence Dossier",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .badge-public {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-private {
        background-color: #F3E8FF;
        color: #6B21A8;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-time {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #10B981;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-left: 8px;
    }
    .news-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #3B82F6;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .source-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 25px;
        margin-bottom: 15px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 6px;
    }
    .progress-card {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0 14px 0;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
    }
    .progress-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        gap: 12px;
    }
    .progress-title {
        display: flex;
        align-items: center;
        gap: 9px;
        font-size: 0.98rem;
        font-weight: 700;
        color: #0F172A;
    }
    .progress-right {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .progress-pct {
        font-size: 1.35rem;
        font-weight: 800;
        color: #1D4ED8;
        font-variant-numeric: tabular-nums;
    }
    .progress-pct.complete {
        color: #059669;
    }
    .progress-pct.error {
        color: #DC2626;
    }
    .progress-elapsed {
        font-size: 0.82rem;
        font-weight: 600;
        color: #475569;
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        border-radius: 999px;
        padding: 3px 10px;
        font-variant-numeric: tabular-nums;
    }
    .progress-track {
        width: 100%;
        height: 14px;
        background: #E2E8F0;
        border-radius: 999px;
        overflow: hidden;
        position: relative;
    }
    .progress-fill {
        height: 100%;
        border-radius: 999px;
        transition: width 0.4s ease;
    }
    .progress-fill.running {
        background: linear-gradient(90deg, #2563EB 0%, #3B82F6 50%, #06B6D4 100%);
        background-size: 200% 100%;
        animation: progress-shimmer 1.8s linear infinite;
    }
    .progress-fill.complete {
        background: linear-gradient(90deg, #059669 0%, #10B981 100%);
    }
    .progress-fill.error {
        background: linear-gradient(90deg, #DC2626 0%, #EF4444 100%);
    }
    .progress-stage {
        margin-top: 9px;
        font-size: 0.88rem;
        color: #475569;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
    }
    .live-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #2563EB;
        display: inline-block;
        animation: live-pulse 1.2s ease-in-out infinite;
    }
    .live-dot.complete {
        background-color: #10B981;
        animation: none;
    }
    .live-dot.error {
        background-color: #EF4444;
        animation: none;
    }
    @keyframes progress-shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.35; transform: scale(0.8); }
    }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Sidebar
with st.sidebar:
    st.markdown("### 🤖 Multi-Agent Team")
    st.markdown("""
    * **👑 Parent Agent**: Research Director
    * **📊 Subagent 1**: Financial Analyst (Deterministic Math)
    * **📰 Subagent 2**: News & Sentiment Scout
    * **🏛️ Subagent 3**: Corporate Biographer
    * **🛡️ Subagent 4**: QA Critic & Fact-Checker
    * **📑 Subagent 5**: PDF & Dossier Publisher
    """)
    st.divider()
    
    # Backend Health Check
    backend_online = False
    provider_name = "Checking..."
    try:
        resp = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        if resp.status_code == 200:
            backend_online = True
            provider_name = resp.json().get("llm_provider", "gemini").upper()
    except Exception:
        backend_online = False

    if backend_online:
        st.success(f"🟢 **FastAPI Backend**: Online")
        st.info(f"⚡ **Active LLM**: {provider_name}")
    else:
        from config import get_config
        cfg = get_config()
        st.info(f"🟡 **Direct Agent Mode** | ⚡ **Active LLM**: {cfg['PROVIDER'].upper()}")
        
    st.divider()
    preset = None

# Header
st.markdown('<div class="main-header">Autonomous Market & Company Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">In-Depth Multi-Agent Intelligence Dossier with Verified Financials, Corporate History & Real-Time News</div>', unsafe_allow_html=True)

# Search Input
if "active_research" not in st.session_state:
    st.session_state["active_research"] = None
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = {}
if "execution_logs" not in st.session_state:
    st.session_state["execution_logs"] = []

target_input = st.text_input(
    "Enter Company Name or Stock Ticker:",
    value=preset if preset else "",
    placeholder="Enter a company name or stock ticker..."
)

execute_btn = st.button("🔍 Launch Deep Multi-Agent Investigation", type="primary", **STRETCH_KW)

if execute_btn or preset:
    query_target = (preset if preset else target_input).strip()
    if not query_target:
        st.warning("⚠️ Please enter a company name or stock ticker to begin the investigation.")
        st.stop()

    progress_placeholder = st.empty()
    log_placeholder = st.empty()
    run_start_ts = time.time()
    tracker = {
        "pct": 2,
        "cap": 9,
        "agent": "Research Supervisor",
        "message": f"Initializing multi-agent pipeline for '{query_target}'...",
        "subagents_done": 0,
        "state": "running",
    }
    st.session_state["execution_logs"] = []

    def render_execution_log(elapsed_s):
        rows = st.session_state["execution_logs"]
        with log_placeholder.container():
            with st.expander(f"Execution log ({len(rows)} events) — {elapsed_s:.1f}s elapsed", expanded=True):
                if not rows:
                    st.caption("Waiting for the first agent event...")
                log_lines = []
                for log in rows[-30:]:
                    icon = "✅" if log["status"] in ("completed", "complete") else "⚙️"
                    log_lines.append(f"{icon} [{log['elapsed']:.1f}s] {log['agent']} — {log['message']}")
                st.markdown(
                    "<div style='max-height:360px;overflow-y:auto;font-size:.82rem;color:#475569;'>" +
                    "<br>".join(log_lines) +
                    "</div>",
                    unsafe_allow_html=True
                )

    def infer_progress_and_cap(evt):
        explicit_pct = evt.get("progress")
        explicit_cap = evt.get("progress_cap")
        if isinstance(explicit_pct, (int, float)):
            pct = max(tracker["pct"], min(100, int(explicit_pct)))
            cap = int(explicit_cap) if isinstance(explicit_cap, (int, float)) else min(99, pct + 4)
            return pct, max(pct, min(100, cap))

        # Backward-compatible inference if an older backend process omits `progress`
        st_name = (evt.get("status") or "").lower()
        ag_name = (evt.get("agent") or "").lower()
        if st_name == "started":
            return max(tracker["pct"], 5), 9
        if st_name == "resolving":
            return max(tracker["pct"], 10), 19
        if st_name == "completed" and "resolver" in ag_name:
            return max(tracker["pct"], 20), 25
        if st_name == "fetching_bio":
            return max(tracker["pct"], 26), 31
        if st_name == "classified":
            return max(tracker["pct"], 32), 35
        if st_name in ("dispatching", "running"):
            return max(tracker["pct"], 38), 49
        if st_name == "completed":
            tracker["subagents_done"] += 1
            milestones = [(50, 61), (62, 73), (74, 77)]
            m_pct, m_cap = milestones[min(tracker["subagents_done"] - 1, len(milestones) - 1)]
            return max(tracker["pct"], m_pct), m_cap
        if st_name == "synthesizing":
            return max(tracker["pct"], 78), 87
        if st_name == "verifying":
            return max(tracker["pct"], 88), 93
        if st_name == "publishing":
            return max(tracker["pct"], 94), 98
        if st_name == "complete":
            return 100, 100
        return tracker["pct"], tracker["cap"]

    def render_progress(pct, agent, message, elapsed_s, state="running"):
        pct_clamped = max(0, min(100, int(pct)))
        safe_target = html.escape(query_target)
        safe_agent = html.escape(agent or "Multi-Agent System")
        safe_msg = html.escape(message or "Processing...")

        if state == "complete":
            title_html = f"<span class='live-dot complete'></span><span>Investigation Complete: {safe_target}</span>"
            status_tag = "All agents finished"
        elif state == "error":
            title_html = f"<span class='live-dot error'></span><span>Investigation Interrupted: {safe_target}</span>"
            status_tag = "Error encountered"
        else:
            title_html = f"<span class='live-dot'></span><span>Executing Multi-Agent Research: {safe_target}</span>"
            status_tag = "Task in progress..."

        progress_placeholder.markdown(
            f"""
            <div class="progress-card">
                <div class="progress-top-row">
                    <div class="progress-title">{title_html}</div>
                    <div class="progress-right">
                        <span class="progress-elapsed">⏱️ {elapsed_s:.1f}s</span>
                        <span class="progress-pct {state}">{pct_clamped}%</span>
                    </div>
                </div>
                <div class="progress-track">
                    <div class="progress-fill {state}" style="width: {pct_clamped}%;"></div>
                </div>
                <div class="progress-stage">
                    <span><strong>{safe_agent}</strong> — {safe_msg}</span>
                    <span style="white-space: nowrap; color: #64748B; font-weight: 600;">{status_tag}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_progress(tracker["pct"], tracker["agent"], tracker["message"], 0.0, state="running")
    st.caption("Please wait while the dossier and PDF are prepared. The page will update automatically.")

    dossier = None
    pdf_bytes = None
    execution_time = None
    error_message = None

    def handle_progress_event(evt):
        t = evt.get("time", round(time.time() - run_start_ts, 1))
        agent = evt.get("agent", "")
        msg = evt.get("message", "")
        pct, cap = infer_progress_and_cap(evt)
        tracker["pct"] = pct
        tracker["cap"] = cap
        tracker["agent"] = agent or tracker["agent"]
        tracker["message"] = msg or tracker["message"]
        render_progress(pct, tracker["agent"], tracker["message"], float(t), state="running")
        event_key = (
            round(float(t), 1),
            agent or "Multi-Agent System",
            msg or "Processing...",
            str(evt.get("status") or "running")
        )
        existing_keys = {
            (
                round(float(log["elapsed"]), 1),
                log["agent"],
                log["message"],
                log["status"]
            )
            for log in st.session_state["execution_logs"]
        }
        if event_key not in existing_keys:
            st.session_state["execution_logs"].append({
            "elapsed": float(t),
            "agent": agent or "Multi-Agent System",
            "message": msg or "Processing...",
            "status": str(evt.get("status") or "running")
            })
        render_execution_log(float(t))

    def handle_heartbeat(elapsed_s):
        if tracker["pct"] < tracker["cap"]:
            tracker["pct"] += 1
        render_progress(tracker["pct"], tracker["agent"], tracker["message"], float(elapsed_s), state="running")
        render_execution_log(float(elapsed_s))

    if backend_online:
        try:
            with requests.post(
                f"{API_BASE_URL}/api/research/stream",
                json={"target": query_target},
                stream=True,
                timeout=300
            ) as response:
                if response.status_code == 200:
                    for line in response.iter_lines(chunk_size=1):
                        if line:
                            item = json.loads(line.decode("utf-8"))
                            item_type = item.get("type")
                            if item_type == "progress":
                                handle_progress_event(item["event"])
                            elif item_type == "heartbeat":
                                handle_heartbeat(item.get("elapsed", round(time.time() - run_start_ts, 1)))
                            elif item_type == "done":
                                results = item.get("results", {})
                                dossier = results.get("dossier")
                                pdf_bytes = None
                                execution_time = results.get("execution_time")
                                break
                            elif item_type == "error":
                                error_message = item.get("error")
                elif response.status_code == 404:
                    error_message = "The backend is missing streaming support. Restart the FastAPI server."
        except Exception as exc:
            error_message = f"Streaming request failed: {exc}"

    if not dossier:
        import importlib
        import tools.schemas
        import tools.chart_tool
        import tools.wiki_tool
        import tools.news_tool
        import tools.finance_tool
        import tools.pdf_tool
        import agents.entity_resolver
        import agents.biography_agent
        import agents.financial_agent
        import agents.news_agent
        import agents.qa_validator_agent
        import agents.supervisor

        importlib.reload(tools.schemas)
        importlib.reload(tools.chart_tool)
        importlib.reload(tools.wiki_tool)
        importlib.reload(tools.news_tool)
        importlib.reload(tools.finance_tool)
        importlib.reload(tools.pdf_tool)
        importlib.reload(agents.entity_resolver)
        importlib.reload(agents.biography_agent)
        importlib.reload(agents.financial_agent)
        importlib.reload(agents.news_agent)
        importlib.reload(agents.qa_validator_agent)
        importlib.reload(agents.supervisor)

        from agents.supervisor import ResearchSupervisor
        supervisor = ResearchSupervisor()
        local_queue = queue.Queue()

        def on_progress(evt):
            local_queue.put({"type": "progress", "event": evt})

        def run_local_worker():
            try:
                res = supervisor.run_investigation(query_target, progress_callback=on_progress)
                local_queue.put({"type": "done", "results": res})
            except Exception as exc:
                local_queue.put({"type": "error", "error": str(exc)})
            finally:
                local_queue.put(None)

        worker = threading.Thread(target=run_local_worker, daemon=True)
        worker.start()

        while True:
            try:
                item = local_queue.get(timeout=1.2)
            except queue.Empty:
                if not worker.is_alive():
                    break
                handle_heartbeat(round(time.time() - run_start_ts, 1))
                continue
            if item is None:
                break
            item_type = item.get("type")
            if item_type == "progress":
                handle_progress_event(item["event"])
            elif item_type == "done":
                results = item.get("results", {})
                dossier = results.get("dossier")
                pdf_bytes = results.get("pdf_bytes")
                execution_time = results.get("execution_time")
            elif item_type == "error":
                error_message = item.get("error")

    final_elapsed = float(execution_time) if execution_time else round(time.time() - run_start_ts, 1)
    if dossier:
        render_progress(100, "Research Supervisor", f"Intelligence dossier & PDF compiled in {final_elapsed:.1f}s.", final_elapsed, state="complete")
        st.session_state["execution_logs"].append({
            "elapsed": final_elapsed,
            "agent": "Research Supervisor",
            "message": "Intelligence dossier & PDF compiled.",
            "status": "complete"
        })
        render_execution_log(final_elapsed)
        st.session_state["active_research"] = {
            "dossier": dossier,
            "pdf_bytes": pdf_bytes,
            "execution_time": final_elapsed,
            "query_target": query_target
        }
    else:
        render_progress(tracker["pct"], "Research Supervisor", error_message or "Investigation did not return a dossier.", final_elapsed, state="error")


# Render Active Dossier (Persisted in st.session_state so quick questions and chat never reset the screen)
active_research = st.session_state.get("active_research")
if active_research and active_research.get("dossier"):
    dossier = active_research["dossier"]
    pdf_bytes = active_research.get("pdf_bytes")
    execution_time = active_research.get("execution_time")
    query_target = active_research.get("query_target", "")
    is_public = dossier.get("is_public", False)
    resolved_entity = dossier.get("resolved_entity") or dossier.get("shared_state", {}).get("resolved_entity") or {}
    entity_type = dossier.get("entity_type") or resolved_entity.get("entity_type") or ("PUBLIC" if is_public else "PRIVATE")
    metrics = dossier.get("metrics", {})
    company_name = dossier.get("company_name", query_target)
    ticker = dossier.get("ticker", "UNLISTED")
    final_time = dossier.get("execution_time") or execution_time
    time_badge = f"<span class='badge-time'>⏱️ Research Completed in {final_time:.2f}s</span>" if final_time else ""

    # Top Badge & Entity Header
    st.markdown("---")
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        if entity_type == "PUBLIC" and is_public:
            st.markdown(f"## {company_name} <span class='badge-public'>PUBLIC TRADED: {ticker}</span> {time_badge}", unsafe_allow_html=True)
            st.caption(f"Exchange: **{metrics.get('exchange', 'N/A')}** | Sector: **{metrics.get('sector', 'N/A')}** | Industry: **{metrics.get('industry', 'N/A')}**")
        elif entity_type == "SUBSIDIARY":
            parent_co = resolved_entity.get("parent_company") or metrics.get("parent_company") or "Parent Holding Group"
            hq = resolved_entity.get("headquarters") or "Regional Market"
            st.markdown(f"## {company_name} <span class='badge-private'>WHOLLY-OWNED SUBSIDIARY</span> {time_badge}", unsafe_allow_html=True)
            st.caption(f"Parent Ownership: **{parent_co}** | HQ: **{hq}** | Sector: **{resolved_entity.get('sector', 'Telecom & Digital')}**")
        else:
            st.markdown(f"## {company_name} <span class='badge-private'>PRIVATELY HELD ENTERPRISE</span> {time_badge}", unsafe_allow_html=True)
            st.caption(f"Status: **Unlisted (No Public Stock Ticker)** | Reporting: **Exempt from SEC 10-K Filings**")
    
    with header_col2:
        # Download PDF & Excel/CSV Buttons (In-memory, 0 disk files)
        import re
        comp_name = dossier.get("company_name", query_target)
        first_word = comp_name.split()[0] if comp_name else query_target
        file_base = re.sub(r'[^a-zA-Z0-9]+', '', first_word).lower()
        if not file_base or len(file_base) < 2:
            file_base = re.sub(r'[^a-zA-Z0-9]+', '_', query_target).strip('_').lower()
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            safe_href = f"{API_BASE_URL}/api/pdf?target={requests.utils.quote(query_target)}"
            st.markdown(
                f"<a href=\"{safe_href}\" target=\"_blank\" "
                f"style=\"display:block;text-align:center;padding:.55rem .8rem;"
                f"border-radius:.5rem;background:#1D4ED8;color:white;text-decoration:none;"
                f"font-weight:700;\">📄 PDF Dossier</a>",
                unsafe_allow_html=True
            )
        with btn_col2:
            from tools.export_tool import generate_excel_or_csv_export
            csv_bytes, csv_fn, csv_mime = generate_excel_or_csv_export(dossier)
            st.download_button(
                label="📊 Excel / CSV",
                data=csv_bytes,
                file_name=csv_fn,
                mime=csv_mime,
                **STRETCH_KW
            )

    # 1. 30-Second Executive Verdict & Bull vs. Bear Matrix
    memo = dossier.get("executive_memo")
    if not memo:
        from tools.intelligence_tool import generate_executive_memo
        memo = generate_executive_memo(dossier)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-radius: 10px; padding: 18px 22px; color: #FFFFFF; margin-top: 15px; margin-bottom: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 10px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">
                ⚡ 30-Second Executive Verdict: <span style="color: {memo.get('badge_color', '#10B981')};">{memo.get('stance', 'BULLISH')}</span>
            </div>
            <div style="background: rgba(255,255,255,0.12); padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                Overall Health: <span style="color: #38BDF8;">{memo.get('health_score', 80)}/100</span> ({memo.get('letter_grade', 'Strong')})
            </div>
        </div>
        <div style="font-size: 0.95rem; color: #CBD5E1; line-height: 1.5;">
            <b>Core Takeaway:</b> {memo.get('takeaway', '')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_pros, col_cons = st.columns(2)
    with col_pros:
        st.markdown("""
        <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px;">
            <div style="font-weight: 700; color: #166534; font-size: 0.95rem; margin-bottom: 8px;">
                🟢 Top 3 Upside Catalysts & Strengths (Pros)
            </div>
        """, unsafe_allow_html=True)
        for pro in memo.get("pros", []):
            st.markdown(f"<div style='color: #14532D; font-size: 0.88rem; margin-bottom: 6px;'>• {pro}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_cons:
        st.markdown("""
        <div style="background-color: #FEF2F2; border: 1px solid #FECACA; border-left: 4px solid #DC2626; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px;">
            <div style="font-weight: 700; color: #991B1B; font-size: 0.95rem; margin-bottom: 8px;">
                🔴 Top 3 Downside Risks & Headwinds (Cons)
            </div>
        """, unsafe_allow_html=True)
        for con in memo.get("cons", []):
            st.markdown(f"<div style='color: #7F1D1D; font-size: 0.88rem; margin-bottom: 6px;'>• {con}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Enterprise Health & Risk Scorecard (0-100)
    scores = dossier.get("health_scorecard")
    if not scores:
        from tools.intelligence_tool import calculate_health_scores
        scores = calculate_health_scores(dossier)

    st.markdown("### 🛡️ Enterprise Health & Risk Scorecard (0–100)")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric("Financial Strength", f"{scores['financial_strength']}/100")
        st.progress(scores["financial_strength"] / 100.0)
        st.caption(f"{scores['descriptors']['financial_strength']}")
    with sc2:
        st.metric("Growth Momentum", f"{scores['growth_momentum']}/100")
        st.progress(scores["growth_momentum"] / 100.0)
        st.caption(f"{scores['descriptors']['growth_momentum']}")
    with sc3:
        st.metric("Valuation Score", f"{scores['valuation_score']}/100")
        st.progress(scores["valuation_score"] / 100.0)
        st.caption(f"{scores['descriptors']['valuation_score']}")
    with sc4:
        st.metric("Safety & Risk Index", f"{scores['safety_risk_index']}/100")
        st.progress(scores["safety_risk_index"] / 100.0)
        st.caption(f"{scores['descriptors']['safety_risk_index']}")

    st.divider()

    # KPI Metrics Cards
    st.markdown("### 📊 Fundamental Snapshot (Single Source of Truth)")
    if entity_type == "PUBLIC" and is_public:
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Stock Price", str(metrics.get("current_price", "N/A")))
        kpi2.metric("Market Cap", str(metrics.get("market_cap", "N/A")))
        kpi3.metric("Trailing P/E", str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A"))))
        kpi4.metric("Forward P/E", str(metrics.get("forward_pe", "N/A")))
        kpi5.metric("Consensus Rating", str(metrics.get("analyst_rating", "N/A")), delta=f"Target: {metrics.get('analyst_target_price', 'N/A')}")
        st.markdown("#### Balance Sheet & Capital Efficiency")
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.metric("Free Cash Flow", str(metrics.get("free_cash_flow", "N/A")))
        b2.metric("Total Debt", str(metrics.get("total_debt", "N/A")))
        b3.metric("Net Debt", str(metrics.get("net_debt", "N/A")))
        b4.metric("ROIC", str(metrics.get("roic", "N/A")))
        b5.metric("Debt / Equity", str(metrics.get("debt_to_equity", "N/A")))
    elif entity_type == "SUBSIDIARY":
        sub_kpis = resolved_entity.get("subsidiary_kpis") or metrics.get("subsidiary_kpis") or {}
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Entity Type", "Wholly-Owned Subsidiary")
        s2.metric("Parent Company", str(resolved_entity.get("parent_company", "Parent Group")).split("(")[0].strip())
        s3.metric("Functional Currency", str(resolved_entity.get("local_currency", "Local")))
        s4.metric("Scale / Subs", str(sub_kpis.get("subscribers", "Not disclosed")).split("(")[0].strip())
    else:
        priv_fin = resolved_entity.get("private_financials") or metrics.get("private_financials") or dossier.get("shared_state", {}).get("private_financials") or {}
        val_str = priv_fin.get("latest_valuation_headline") or "Private Valuation"
        fund_str = priv_fin.get("latest_funding_headline") or "Venture Funding"
        rev_str = priv_fin.get("latest_revenue_headline") or "Commercial Scale"
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Entity Classification", "Privately Held")
        p2.metric("Latest Valuation", val_str)
        p3.metric("Capital Raised", fund_str)
        p4.metric("Commercial Scale", rev_str)

    # Executive Summary Box
    st.markdown("### 🧠 Executive Summary & Strategic Synthesis")
    st.markdown(dossier.get("executive_summary", "No summary available."))

    # Tabbed Detailed View
    tab_bio, tab_fin, tab_news, tab_strategy, tab_raw = st.tabs([
        "🏛️ Corporate History & Moat",
        "📈 Financial & Valuation Analysis",
        "📰 Recent News & Media Sentiment",
        "🎯 Strategic Outlook & Risks",
        "📄 Raw Multi-Agent Data"
    ])

    with tab_bio:
        st.markdown("### Detailed Corporate Background & Business Architecture")
        st.markdown(dossier.get("corporate_background", "No background available."))

    with tab_fin:
        # 3. Competitive Peer Benchmarking Matrix
        competitors = dossier.get("competitor_comparison")
        if not competitors:
            from tools.intelligence_tool import get_competitor_comparison
            competitors = get_competitor_comparison(dossier)

        if competitors:
            st.markdown("### 🏆 Competitive Peer Benchmarking Matrix")
            st.caption(f"Side-by-side performance & valuation benchmarking against primary industry peers:")
            try:
                import pandas as pd
                peer_rows = [{
                    "Company": f"⭐ {company_name} (Target)",
                    "Ticker": ticker,
                    "Valuation": str(metrics.get("market_cap", "Target")),
                    "P/E Multiple": str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A"))),
                    "YoY Growth": str(metrics.get("revenue_growth_yoy", "Baseline")),
                    "Net Margin": str(metrics.get("profit_margins", "Reported")),
                    "Strategic Edge / Moat": "Target Enterprise"
                }]
                for c in competitors:
                    peer_rows.append({
                        "Company": c.get("name", "Competitor"),
                        "Ticker": c.get("ticker", "N/A"),
                        "Valuation": c.get("market_cap", "N/A"),
                        "P/E Multiple": c.get("pe_ratio", "N/A"),
                        "YoY Growth": c.get("revenue_growth", "N/A"),
                        "Net Margin": c.get("net_margin", "N/A"),
                        "Strategic Edge / Moat": c.get("edge", "N/A")
                    })
                df_peers = pd.DataFrame(peer_rows)
                st.dataframe(df_peers, hide_index=True, **STRETCH_KW)
            except Exception:
                pass
            st.divider()

        chart_data = metrics.get("chart_data") if (entity_type == "PUBLIC" and is_public) else None
        if isinstance(chart_data, dict) and (
            len(chart_data.get("price_history") or []) >= 5
            or len(chart_data.get("annual_financials") or []) >= 2
            or len(chart_data.get("margins") or []) >= 1
        ):
            try:
                import pandas as pd
                import altair as alt

                st.markdown("### 📊 Interactive Market Performance & Financial Charts")
                c_curr = chart_data.get("currency", "USD")
                reporting_curr = chart_data.get("reporting_currency", c_curr)
                price_hist = chart_data.get("price_history") or []
                price_sum = chart_data.get("price_summary") or {}

                # 1. 1-Year Stock Price & 50-Day Moving Average
                if len(price_hist) >= 5:
                    df_p = pd.DataFrame(price_hist)
                    df_p["date"] = pd.to_datetime(df_p["date"])
                    ret_1y = price_sum.get("return_1y_pct", 0.0)
                    ret_badge = f"+{ret_1y:.1f}%" if ret_1y >= 0 else f"{ret_1y:.1f}%"
                    st.caption(f"**1-Year Price Trend & 50-Day Moving Average ({ticker}, {c_curr})** — 1Y Return: **{ret_badge}**")

                    y_min = float(df_p["close"].min()) * 0.95
                    y_max = float(df_p["close"].max()) * 1.05
                    y_scale = alt.Scale(domain=[max(0.0, y_min), y_max])

                    area = alt.Chart(df_p).mark_area(
                        line={"color": "#2563EB", "strokeWidth": 2},
                        color=alt.Gradient(
                            gradient="linear",
                            stops=[
                                alt.GradientStop(color="rgba(37, 99, 235, 0.28)", offset=0),
                                alt.GradientStop(color="rgba(37, 99, 235, 0.02)", offset=1),
                            ],
                            x1=1, x2=1, y1=0, y2=1
                        )
                    ).encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("close:Q", title=f"Price ({c_curr})", scale=y_scale),
                        tooltip=[
                            alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                            alt.Tooltip("close:Q", title=f"Close ({c_curr})", format=",.2f"),
                            alt.Tooltip("sma50:Q", title=f"50D SMA ({c_curr})", format=",.2f"),
                        ]
                    )

                    sma_df = df_p.dropna(subset=["sma50"])
                    if not sma_df.empty:
                        sma_line = alt.Chart(sma_df).mark_line(
                            color="#D97706", strokeDash=[5, 4], strokeWidth=1.8
                        ).encode(
                            x="date:T",
                            y=alt.Y("sma50:Q", scale=y_scale)
                        )
                        price_chart = (area + sma_line).properties(height=300).interactive()
                    else:
                        price_chart = area.properties(height=300).interactive()

                    st.altair_chart(price_chart, **STRETCH_KW)

                # 2. Side-by-side Annual Revenue vs. Net Income & Margin Profile
                ann_fin = chart_data.get("annual_financials") or []
                margins_data = chart_data.get("margins") or []
                if len(ann_fin) >= 2 or len(margins_data) >= 1:
                    ch_col1, ch_col2 = st.columns([3, 2]) if (len(ann_fin) >= 2 and len(margins_data) >= 1) else (st.container(), st.container())

                    if len(ann_fin) >= 2:
                        with ch_col1:
                            st.caption(f"**Annual Revenue vs. Net Income ({reporting_curr} Billions)**")
                            rows_long = []
                            for r in ann_fin:
                                if r.get("revenue") is not None:
                                    rows_long.append({"Year": r["year"], "Metric": "Revenue", "Value_B": round(r["revenue"] / 1e9, 2)})
                                if r.get("net_income") is not None:
                                    rows_long.append({"Year": r["year"], "Metric": "Net Income", "Value_B": round(r["net_income"] / 1e9, 2)})
                            df_ann = pd.DataFrame(rows_long)
                            bar_chart = alt.Chart(df_ann).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                                x=alt.X("Year:N", title="Fiscal Year", axis=alt.Axis(labelAngle=0)),
                                xOffset="Metric:N",
                                y=alt.Y("Value_B:Q", title=f"{reporting_curr} (Billions)"),
                                color=alt.Color(
                                    "Metric:N",
                                    scale=alt.Scale(domain=["Revenue", "Net Income"], range=["#1E40AF", "#10B981"]),
                                    legend=alt.Legend(orient="top", title=None)
                                ),
                                tooltip=[
                                    alt.Tooltip("Year:N", title="Fiscal Year"),
                                    alt.Tooltip("Metric:N", title="Metric"),
                                    alt.Tooltip("Value_B:Q", title=f"Amount ({reporting_curr} B)", format=",.2f"),
                                ]
                            ).properties(height=260)
                            st.altair_chart(bar_chart, **STRETCH_KW)

                    if len(margins_data) >= 1:
                        with ch_col2:
                            st.caption("**Profitability Margin Profile (%)**")
                            df_m = pd.DataFrame(margins_data)
                            m_bars = alt.Chart(df_m).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, size=26).encode(
                                y=alt.Y("label:N", sort=None, title=None),
                                x=alt.X("value:Q", title="Margin (%)"),
                                color=alt.Color(
                                    "label:N",
                                    scale=alt.Scale(
                                        domain=["Gross Margin", "Operating Margin", "Net Profit Margin"],
                                        range=["#2563EB", "#0891B2", "#10B981"]
                                    ),
                                    legend=None
                                ),
                                tooltip=[
                                    alt.Tooltip("label:N", title="Margin"),
                                    alt.Tooltip("value:Q", title="Percentage (%)", format=".2f"),
                                ]
                            )
                            m_text = m_bars.mark_text(align="left", dx=5, fontWeight="bold", color="#0F172A").encode(
                                text=alt.Text("value:Q", format=".2f")
                            )
                            st.altair_chart((m_bars + m_text).properties(height=260), **STRETCH_KW)

                st.divider()
            except Exception:
                pass

        st.markdown("### In-Depth Financial & Valuation Critique")
        st.markdown(dossier.get("financial_analysis", "No financial analysis available."))

    with tab_news:
        st.markdown("### Media Sentiment & Key Catalysts")
        st.markdown(dossier.get("recent_news_analysis", "No news analysis."))
        
        # Explicit Detailed Sources Heading requested by user
        st.markdown('<div class="source-header">Here are the Detailed Sources:</div>', unsafe_allow_html=True)
        articles = dossier.get("news_articles", [])
        if articles:
            for idx, art in enumerate(articles, 1):
                st.markdown(f"""
                <div class="news-card">
                    <div style="font-size: 0.82rem; color: #64748B; font-weight: 600; text-transform: uppercase;">
                        Source #{idx} | {art.get('source')}
                    </div>
                    <a href="{art.get('url')}" target="_blank" style="text-decoration:none; font-weight:700; color:#1E40AF; font-size:1.05rem;">
                        {art.get('title')} ↗
                    </a>
                    <div style="color:#64748B; font-size:0.85rem; margin-top:4px;">
                        Published Date: <b>{art.get('date')}</b>
                    </div>
                    <div style="font-size:0.8rem; color:#94A3B8; margin-top:3px; word-break: break-all;">
                        URL: <a href="{art.get('url')}" target="_blank" style="color:#60A5FA;">{art.get('url')}</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No recent external headlines discovered.")

    with tab_strategy:
        st.markdown("### Comprehensive Strategic Outlook & Key Risk Vectors")
        st.markdown(dossier.get("strategic_outlook", "No outlook details."))

    with tab_raw:
        st.markdown("### Structured Multi-Agent JSON Dossier")
        st.json(dossier)

    # 4. Interactive Q&A Assistant Over Completed Dossier (Isolated fragment: instant in-memory responses, no full-page dimming/lock)
    @st.fragment
    def render_interactive_qa(qa_dossier, target_name):
        st.markdown("---")
        st.markdown(f"### 💬 Interactive Dossier Assistant: Ask Anything About {target_name}")
        st.caption("Ask specific follow-up questions to query this dossier in real-time (Instant in-memory response without re-running the multi-agent pipeline).")

        if "qa_history" not in st.session_state:
            st.session_state.qa_history = {}
        if target_name not in st.session_state.qa_history:
            st.session_state.qa_history[target_name] = []

        # Example Quick Questions Chips
        chip1, chip2, chip3, chip4 = st.columns(4)
        quick_q = None
        with chip1:
            if st.button("👔 Who is the CEO & Leaders?", key="q_ceo", **STRETCH_KW):
                quick_q = f"Who is the CEO and active leadership of {target_name}?"
        with chip2:
            if st.button("💰 What are their Margins & Rev?", key="q_fin", **STRETCH_KW):
                quick_q = f"What are {target_name}'s profit margins and revenue numbers?"
        with chip3:
            if st.button("⚠️ What are the Biggest Risks?", key="q_risk", **STRETCH_KW):
                quick_q = f"What are the top risks and regulatory headwinds facing {target_name}?"
        with chip4:
            if st.button("🚀 What are the Core Products?", key="q_prod", **STRETCH_KW):
                quick_q = f"What are the primary products and business divisions of {target_name}?"

        user_q = st.chat_input(f"Ask a question about {target_name}...")
        active_question = user_q or quick_q

        if active_question:
            from tools.intelligence_tool import answer_question_from_dossier
            answer = answer_question_from_dossier(qa_dossier, active_question)

            st.session_state.qa_history[target_name].append({
                "question": active_question,
                "answer": answer
            })

        # Display QA conversation history for this company
        for chat_item in st.session_state.qa_history[target_name]:
            with st.chat_message("user"):
                st.write(chat_item["question"])
            with st.chat_message("assistant"):
                st.write(chat_item["answer"])

    render_interactive_qa(dossier, company_name)
