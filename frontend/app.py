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
    * **📊 Subagent 1**: Financial Analyst
    * **📰 Subagent 2**: News & Sentiment Scout
    * **🏛️ Subagent 3**: Corporate Biographer
    * **📑 Subagent 4**: PDF & Dossier Publisher
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
        st.warning("🟡 **FastAPI Backend**: Offline (Direct Agent Mode Active)")
        
    st.divider()
    st.markdown("### 💡 Quick Search Examples")
    preset = None
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Systems Limited", use_container_width=True): preset = "Systems Limited"
        if st.button("NVIDIA", use_container_width=True): preset = "NVDA"
        if st.button("Apple", use_container_width=True): preset = "AAPL"
    with col2:
        if st.button("OpenAI", use_container_width=True): preset = "OpenAI"
        if st.button("Tesla", use_container_width=True): preset = "TSLA"
        if st.button("Emumba", use_container_width=True): preset = "Emumba"

# Header
st.markdown('<div class="main-header">Autonomous Market & Company Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">In-Depth Multi-Agent Intelligence Dossier with Verified Financials, Corporate History & Real-Time News</div>', unsafe_allow_html=True)

# Search Input
target_input = st.text_input(
    "Enter Company Name or Stock Ticker:",
    value=preset if preset else "Systems Limited",
    placeholder="e.g. Systems Limited, OpenAI, NVDA, Emumba, Apple, TSLA..."
)

execute_btn = st.button("🔍 Launch Deep Multi-Agent Investigation", type="primary", use_container_width=True)

if execute_btn or preset:
    with st.status("🚀 Parent Agent orchestrating deep investigation...", expanded=True) as status:
        st.write("🔍 **Parent Agent**: Decomposing query and resolving verified entity classification...")
        
        dossier = None
        pdf_path = None
        
        # 1. Attempt call to FastAPI backend
        if backend_online:
            st.write("🌐 Querying FastAPI Backend (`POST /api/research`)...")
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/research",
                    json={"target": target_input},
                    timeout=90
                )
                if response.status_code == 200:
                    payload = response.json()
                    dossier = payload.get("dossier")
                    pdf_filename = payload.get("pdf_filename")
                    pdf_path = os.path.join("reports", pdf_filename)
                else:
                    st.error(f"Backend error: {response.text}")
            except Exception as e:
                st.warning(f"Backend request failed: {e}. Falling back to direct agent execution.")

        # 2. Fallback: Direct Agent Execution if backend not running
        if not dossier:
            st.write("⚡ Executing Multi-Agent supervisor directly...")
            from agents.supervisor import ResearchSupervisor
            supervisor = ResearchSupervisor()
            results = supervisor.run_investigation(target_input)
            dossier = results["dossier"]
            pdf_path = results["pdf_path"]

        st.write("✅ All subagents delivered in-depth intelligence. Compiling complete executive briefing...")
        status.update(label="🎯 Deep Investigation Complete!", state="complete", expanded=False)

    if dossier:
        is_public = dossier.get("is_public", False)
        metrics = dossier.get("metrics", {})
        company_name = dossier.get("company_name", target_input)
        ticker = dossier.get("ticker", "UNLISTED")

        # Top Badge & Entity Header
        st.markdown("---")
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            if is_public:
                st.markdown(f"## {company_name} <span class='badge-public'>PUBLIC TRADED: {ticker}</span>", unsafe_allow_html=True)
                st.caption(f"Exchange: **{metrics.get('exchange', 'N/A')}** | Sector: **{metrics.get('sector', 'N/A')}** | Industry: **{metrics.get('industry', 'N/A')}**")
            else:
                st.markdown(f"## {company_name} <span class='badge-private'>PRIVATELY HELD ENTERPRISE</span>", unsafe_allow_html=True)
                st.caption(f"Status: **Unlisted (No Public Stock Ticker)** | Reporting: **Exempt from SEC 10-K Filings**")
        
        with header_col2:
            # Download PDF Button
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="📥 Download Executive PDF Dossier",
                    data=pdf_bytes,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    use_container_width=True
                )

        # KPI Metrics Cards
        st.markdown("### 📊 Fundamental Snapshot")
        if is_public:
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Stock Price", str(metrics.get("current_price", "N/A")))
            kpi2.metric("Market Cap", str(metrics.get("market_cap", "N/A")))
            kpi3.metric("P/E Ratio", str(metrics.get("pe_ratio", "N/A")))
            kpi4.metric("Consensus Rating", str(metrics.get("analyst_rating", "N/A")), delta=f"Target: {metrics.get('analyst_target_price', 'N/A')}")
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
