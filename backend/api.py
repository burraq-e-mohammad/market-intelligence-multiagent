import sys
import os

# Auto-mount local project root & virtual environment site-packages
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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import queue
import threading
import time
from agents.supervisor import ResearchSupervisor
import config
from fastapi.responses import Response

_pdf_cache: Dict[str, bytes] = {}

app = FastAPI(
    title="Autonomous Market Intelligence Multi-Agent API",
    description="Backend API powering the Parent-Subagents Market Research System",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supervisor = ResearchSupervisor()

class ResearchRequest(BaseModel):
    target: str

class QARequest(BaseModel):
    target: Optional[str] = None
    question: str
    dossier: Dict[str, Any]

class QAResponse(BaseModel):
    question: str
    answer: str

class ResearchResponse(BaseModel):
    status: str
    target: str
    is_public: bool
    dossier: Dict[str, Any]
    execution_time: Optional[float] = None
    pdf_filename: Optional[str] = None
    md_filename: Optional[str] = None

@app.get("/")
def root():
    cfg = config.get_config()
    return {
        "service": "Autonomous Market Intelligence API",
        "active_provider": cfg["PROVIDER"].upper(),
        "status": "online"
    }

@app.get("/api/health")
def health_check():
    cfg = config.get_config()
    return {
        "status": "healthy",
        "llm_provider": cfg["PROVIDER"],
        "gemini_configured": bool(cfg["GEMINI_API_KEY"]),
        "groq_configured": bool(cfg["GROQ_API_KEY"])
    }

@app.post("/api/research", response_model=ResearchResponse)
def conduct_research(request: ResearchRequest):
    """
    Main Multi-Agent Orchestration Endpoint.
    Parent Agent delegates to Financial, News, and Biographer subagents,
    synthesizes intelligence, and generates in-memory reports (0 disk files written).
    """
    target = request.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target company name or ticker is required.")
        
    try:
        results = supervisor.run_investigation(target)
        dossier = dict(results["dossier"])
        if isinstance(dossier.get("shared_state"), dict):
            ss_clean = {k: v for k, v in dossier["shared_state"].items() if k != "bio_tool_result"}
            dossier["shared_state"] = ss_clean
        
        return {
            "status": "success",
            "target": target,
            "is_public": dossier.get("is_public", False),
            "dossier": dossier,
            "execution_time": results.get("execution_time")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-Agent investigation failed: {str(e)}")

@app.post("/api/research/stream")
def conduct_research_stream(request: ResearchRequest):
    """
    Streaming endpoint providing real-time multi-agent progression events and final intelligence dossier.
    """
    target = request.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target company name or ticker is required.")

    def event_stream():
        event_queue = queue.Queue()

        def on_progress(event):
            event_queue.put({"type": "progress", "event": event})

        def run_worker():
            try:
                try:
                    results = supervisor.run_investigation(target, progress_callback=on_progress)
                except TypeError:
                    results = supervisor.run_investigation(target)

                raw_dossier = dict(results.get("dossier") or {})
                if isinstance(raw_dossier.get("shared_state"), dict):
                    raw_dossier["shared_state"] = {
                        k: v for k, v in raw_dossier["shared_state"].items() if k != "bio_tool_result"
                    }
                pdf_raw = results.get("pdf_bytes")
                safe_results = {
                    "dossier": raw_dossier,
                    "execution_time": results.get("execution_time")
                }
                if isinstance(pdf_raw, (bytes, bytearray)):
                    _pdf_cache[target.lower()] = bytes(pdf_raw)
                event_queue.put({"type": "done", "results": safe_results})
            except Exception as exc:
                event_queue.put({"type": "error", "error": str(exc)})
            finally:
                event_queue.put(None)

        worker_thread = threading.Thread(target=run_worker)
        worker_thread.start()
        stream_start = time.time()

        while True:
            try:
                item = event_queue.get(timeout=1.2)
            except queue.Empty:
                if not worker_thread.is_alive():
                    break
                yield json.dumps({"type": "heartbeat", "elapsed": round(time.time() - stream_start, 1)}) + "\n"
                continue
            if item is None:
                break
            yield json.dumps(item, default=str) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/api/pdf")
def download_pdf(target: str):
    """
    Serve generated PDF dossier directly in-memory without saving any files to disk.
    """
    clean = target.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Target company name or ticker required.")
    cached = _pdf_cache.get(clean.lower())
    if cached:
        return Response(
            content=cached,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={clean}_dossier.pdf"}
        )
    results = supervisor.run_investigation(clean)
    pdf_bytes = results.get("pdf_bytes")
    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={clean}_dossier.pdf"}
    )

@app.post("/api/research/qa", response_model=QAResponse)
def answer_dossier_qa(request: QARequest):
    """
    Answers user follow-up questions directly from the synthesized intelligence dossier.
    Instant latency (~1s), does not rerun the multi-agent pipeline.
    """
    q = request.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    from tools.intelligence_tool import answer_question_from_dossier
    answer = answer_question_from_dossier(request.dossier, q)
    return {"question": q, "answer": answer}

@app.post("/api/export/csv")
def export_csv_model(request: Dict[str, Any]):
    """
    Generates a structured financial data model CSV that opens natively in Microsoft Excel.
    """
    from tools.export_tool import generate_excel_or_csv_export
    csv_bytes, filename, mime_type = generate_excel_or_csv_export(request)
    from fastapi.responses import Response
    return Response(
        content=csv_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
