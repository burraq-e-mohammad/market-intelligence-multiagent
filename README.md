# Autonomous Market & Company Intelligence Dossier
### 100% Free Multi-Agent System (FastAPI + Streamlit + Parent-Subagent Architecture)

An autonomous multi-agent intelligence platform that researches any public or private company on demand. It features a hierarchical **Parent Orchestrator (Research Director)** managing three specialized **Subagents**, served via a **FastAPI backend** and visualized on an executive **Streamlit dashboard** with downloadable PDF dossiers.

---

## 🏗️ Architecture

```
                       +----------------------------------+
                       |       STREAMLIT DASHBOARD        |
                       |      http://localhost:8501       |
                       +-----------------+----------------+
                                         |
                                (REST: POST /api/research)
                                         v
                       +----------------------------------+
                       |         FASTAPI BACKEND          |
                       |      http://127.0.0.1:8000       |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |           PARENT AGENT           |
                       |        Research Director         |
                       |    - Decomposes Objectives       |
                       |    - Resolves Public vs Private  |
                       |    - Delegates to Subagents      |
                       |    - Synthesizes Reports         |
                       +-----------------+----------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+------------------+           +--------------------+          +--------------------+
|   SUBAGENT 1     |           |    SUBAGENT 2      |          |    SUBAGENT 3      |
| Financial Analyst|           |    News Scout      |          | Company Biographer |
+--------+---------+           +---------+----------+          +---------+----------+
         |                               |                               |
         v                               v                               v
+------------------+           +--------------------+          +--------------------+
|  TOOL: yfinance  |           | TOOL: Google/Yahoo |          |  TOOL: Wikipedia   |
| Public/Private   |           | Breaking Headlines |          | Web Profiles, Moat |
+------------------+           +--------------------+          +--------------------+
         |                               |                               |
         +-------------------------------+-------------------------------+
                                         |
                                         v (Synthesized Findings)
                       +----------------------------------+
                       |           PARENT AGENT           |
                       |       Executive Synthesis        |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |      PUBLISHER & EXPORTER        |
                       |  - PDF Dossier (FPDF2)           |
                       |  - Markdown Dossier (.md)        |
                       +----------------------------------+
```

---

## 💎 Why Everything Is 100% Free

Every component in this project requires **$0.00, no paid subscriptions, and no mandatory credit card**:

| Component | Technology | Free Tier Details |
| :--- | :--- | :--- |
| **Financial Fundamentals** | `yfinance` | Free live financial market data for public equities + private market auditing. |
| **News & Headlines** | Google RSS & Yahoo Finance | Free real-time news feeds with zero rate-limit blocks. |
| **Corporate History** | `wikipedia-api` + Web Search | Free encyclopedic origins, founders, and moat analysis. |
| **PDF Generation** | `fpdf2` | Fast, lightweight local PDF engine. |
| **Backend API** | `FastAPI` + `Uvicorn` | Open-source Python REST framework with automatic OpenAPI docs. |
| **Frontend UI** | `Streamlit` | Open-source interactive dashboard framework. |
| **LLM Reasoning Engine** | Flexible Choice | **Google Gemini** (Free tier via AI Studio), **Groq** (Free Llama 3.3 tier), **Ollama** (100% Local offline), or **Mock Engine** (instant testing with 0 keys). |

---

## 🚀 How to Run the Project

### 1. Launch Both Backend & Frontend Together
With your virtual environment activated:
```powershell
python run.py
```
This boots:
* 🌐 **Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)
* ⚡ **FastAPI Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Or Run Components Separately
* **Only the FastAPI Backend**:
  ```powershell
  python run.py --backend-only
  # or: uvicorn backend.api:app --reload --port 8000
  ```
* **Only the Streamlit Frontend**:
  ```powershell
  python run.py --frontend-only
  # or: streamlit run frontend/app.py
  ```
* **Interactive CLI Mode**:
  ```powershell
  python main.py --target NVDA
  ```

---

## 📡 FastAPI REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status and active LLM engine info |
| `GET` | `/api/health` | Health check verifying provider keys |
| `POST` | `/api/research` | Multi-agent research pipeline (`{"target": "NVDA"}`) |
| `GET` | `/api/reports/{filename}` | Serves the generated PDF or Markdown dossiers |

---

## 📁 Project Structure

```
Multi Agent Project/
├── .env                      # API keys (Gemini, Groq, Ollama)
├── .env.example              # Template configuration
├── config.py                 # LLM provider routing and settings
├── main.py                   # Standalone CLI runner
├── run.py                    # Unified launcher for FastAPI + Streamlit
├── requirements.txt          # Python dependencies
├── README.md                 # Complete documentation
├── backend/                  # FastAPI REST Microservice
│   ├── __init__.py
│   └── api.py                # Endpoints (/api/research, /api/reports)
├── frontend/                 # Streamlit Web Application
│   ├── __init__.py
│   └── app.py                # Dashboard with KPI cards, tabs & PDF download
├── agents/                   # Multi-Agent Architecture
│   ├── base_agent.py         # Multi-provider LLM caller
│   ├── supervisor.py         # PARENT AGENT: Research Director & Orchestrator
│   ├── financial_agent.py    # SUBAGENT 1: Public/Private Equity Analyst
│   ├── news_agent.py         # SUBAGENT 2: Real-time News Scout
│   └── biography_agent.py    # SUBAGENT 3: Corporate Historian & Strategist
├── tools/                    # Tool Integrations
│   ├── finance_tool.py       # yfinance & entity classification
│   ├── news_tool.py          # Google News RSS & Yahoo feeds
│   ├── wiki_tool.py          # Wikipedia & verified web profiles
│   └── pdf_tool.py           # Styled FPDF2 PDF report builder
└── reports/                  # Generated PDF & Markdown dossiers
```
