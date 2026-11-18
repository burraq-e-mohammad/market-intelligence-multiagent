import streamlit as st
import requests
import os
import json

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
    st.markdown("### 💡 Quick Search Examples")
    preset = None
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Microsoft", use_container_width=True): preset = "Microsoft"
        if st.button("NVIDIA", use_container_width=True): preset = "NVIDIA"
        if st.button("Apple", use_container_width=True): preset = "Apple"
    with col2:
        if st.button("OpenAI", use_container_width=True): preset = "OpenAI"
        if st.button("Tesla", use_container_width=True): preset = "Tesla"
        if st.button("Amazon", use_container_width=True): preset = "Amazon"

# Header
st.markdown('<div class="main-header">Autonomous Market & Company Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">In-Depth Multi-Agent Intelligence Dossier with Verified Financials, Corporate History & Real-Time News</div>', unsafe_allow_html=True)

# Search Input
target_input = st.text_input(
    "Enter Company Name or Stock Ticker:",
    value=preset if preset else "",
    placeholder="e.g. Microsoft, Apple, NVIDIA, OpenAI, Tesla, Amazon, Systems Limited..."
)

execute_btn = st.button("🔍 Launch Deep Multi-Agent Investigation", type="primary", use_container_width=True)

if execute_btn or preset:
    query_target = (preset if preset else target_input).strip()
    if not query_target:
        st.warning("⚠️ Please enter a company name or stock ticker to begin the investigation.")
        st.stop()

    with st.status(f"🚀 Multi-Agent Team Investigating: '{query_target}'...", expanded=True) as status:
        dossier = None
        pdf_bytes = None
        execution_time = None

        # 1. Attempt Streaming Call to FastAPI Backend
        if backend_online:
            try:
                with requests.post(
                    f"{API_BASE_URL}/api/research/stream",
                    json={"target": query_target},
                    stream=True,
                    timeout=300
                ) as response:
                    if response.status_code == 200:
                        for line in response.iter_lines():
                            if line:
                                item = json.loads(line.decode("utf-8"))
                                if item.get("type") == "progress":
                                    evt = item["event"]
                                    t = evt.get("time", 0.0)
                                    agent = evt.get("agent", "")
                                    msg = evt.get("message", "")
                                    status.write(f"⏱️ **[{t:.1f}s]** `{agent}`: {msg}")
                                elif item.get("type") == "done":
                                    results = item.get("results", {})
                                    dossier = results.get("dossier")
                                    pdf_b64 = results.get("pdf_b64")
                                    if pdf_b64:
                                        import base64
                                        pdf_bytes = base64.b64decode(pdf_b64)
                                    else:
                                        pdf_bytes = results.get("pdf_bytes")
                                    execution_time = results.get("execution_time")
                                elif item.get("type") == "error":
                                    status.write(f"⚠️ Worker notice: {item.get('error')}")
                    elif response.status_code == 404:
                        status.write("⚠️ Older FastAPI server detected on port 8000 (missing `/api/research/stream`). Restart backend to enable API streaming; continuing in Direct Mode...")
            except Exception:
                pass

        # 2. Fallback: Direct Agent Execution with live callback
        if not dossier:
            import importlib
            import tools.schemas
            import tools.wiki_tool
            import tools.news_tool
            import tools.finance_tool
            import tools.pdf_tool
            import agents.biography_agent
            import agents.financial_agent
            import agents.news_agent
            import agents.qa_critic
            import agents.supervisor

            importlib.reload(tools.schemas)
            importlib.reload(tools.wiki_tool)
            importlib.reload(tools.news_tool)
            importlib.reload(tools.finance_tool)
            importlib.reload(tools.pdf_tool)
            importlib.reload(agents.biography_agent)
            importlib.reload(agents.financial_agent)
            importlib.reload(agents.news_agent)
            importlib.reload(agents.qa_critic)
            importlib.reload(agents.supervisor)

            from agents.supervisor import ResearchSupervisor
            supervisor = ResearchSupervisor()

            def on_progress(evt):
                t = evt.get("time", 0.0)
                agent = evt.get("agent", "")
                msg = evt.get("message", "")
                status.write(f"⏱️ **[{t:.1f}s]** `{agent}`: {msg}")

            try:
                results = supervisor.run_investigation(query_target, progress_callback=on_progress)
            except TypeError:
                results = supervisor.run_investigation(query_target)

            dossier = results.get("dossier")
            pdf_bytes = results.get("pdf_bytes")
            execution_time = results.get("execution_time")

        time_display = f"{execution_time:.1f}s" if execution_time else "Done"
        status.update(label=f"🎯 Deep Investigation Complete in {time_display}!", state="complete", expanded=False)

    if dossier:
        is_public = dossier.get("is_public", False)
        metrics = dossier.get("metrics", {})
        company_name = dossier.get("company_name", query_target)
        ticker = dossier.get("ticker", "UNLISTED")
        final_time = dossier.get("execution_time") or execution_time
        time_badge = f"<span class='badge-time'>⏱️ Research Completed in {final_time:.2f}s</span>" if final_time else ""

        # Top Badge & Entity Header
        st.markdown("---")
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            if is_public:
                st.markdown(f"## {company_name} <span class='badge-public'>PUBLIC TRADED: {ticker}</span> {time_badge}", unsafe_allow_html=True)
                st.caption(f"Exchange: **{metrics.get('exchange', 'N/A')}** | Sector: **{metrics.get('sector', 'N/A')}** | Industry: **{metrics.get('industry', 'N/A')}**")
            else:
                st.markdown(f"## {company_name} <span class='badge-private'>PRIVATELY HELD ENTERPRISE</span> {time_badge}", unsafe_allow_html=True)
                st.caption(f"Status: **Unlisted (No Public Stock Ticker)** | Reporting: **Exempt from SEC 10-K Filings**")
        
        with header_col2:
            # Download PDF Button (In-memory, 0 disk files)
            if not pdf_bytes and dossier:
                from tools.pdf_tool import generate_pdf_report
                pdf_bytes = generate_pdf_report(dossier)
                
            if pdf_bytes:
                import re
                comp_name = dossier.get("company_name", query_target)
                first_word = comp_name.split()[0] if comp_name else query_target
                file_base = re.sub(r'[^a-zA-Z0-9]+', '', first_word).lower()
                if not file_base or len(file_base) < 2:
                    file_base = re.sub(r'[^a-zA-Z0-9]+', '_', query_target).strip('_').lower()
                
                st.download_button(
                    label="📥 Download Executive PDF Dossier",
                    data=pdf_bytes,
                    file_name=f"{file_base}_intelligence_dossier.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # KPI Metrics Cards
        st.markdown("### 📊 Fundamental Snapshot (Single Source of Truth)")
        if is_public:
            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("Stock Price", str(metrics.get("current_price", "N/A")))
            kpi2.metric("Market Cap", str(metrics.get("market_cap", "N/A")))
            kpi3.metric("Trailing P/E", str(metrics.get("trailing_pe", metrics.get("pe_ratio", "N/A"))))
            kpi4.metric("Forward P/E", str(metrics.get("forward_pe", "N/A")))
            kpi5.metric("Consensus Rating", str(metrics.get("analyst_rating", "N/A")), delta=f"Target: {metrics.get('analyst_target_price', 'N/A')}")
        else:
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Entity Classification", "Privately Held")
            p2.metric("Public Trading", "Unlisted")
            p3.metric("Ownership Structure", "Private / Venture")
            p4.metric("Market Valuation", "Private Rounds")

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
