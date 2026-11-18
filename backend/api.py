from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import json
import base64
import queue
import threading
from agents.supervisor import ResearchSupervisor
import config

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

                # Prepare JSON-safe payload (convert raw pdf_bytes to base64 and omit internal raw tool dump)
                raw_dossier = dict(results.get("dossier") or {})
                if isinstance(raw_dossier.get("shared_state"), dict):
                    raw_dossier["shared_state"] = {
                        k: v for k, v in raw_dossier["shared_state"].items() if k != "bio_tool_result"
                    }
                pdf_raw = results.get("pdf_bytes")
                pdf_b64 = base64.b64encode(pdf_raw).decode("ascii") if isinstance(pdf_raw, (bytes, bytearray)) else None

                safe_results = {
                    "dossier": raw_dossier,
                    "pdf_b64": pdf_b64,
                    "execution_time": results.get("execution_time")
                }
                event_queue.put({"type": "done", "results": safe_results})
            except Exception as exc:
                event_queue.put({"type": "error", "error": str(exc)})
            finally:
                event_queue.put(None)

        worker_thread = threading.Thread(target=run_worker)
        worker_thread.start()

        while True:
            item = event_queue.get()
            if item is None:
                break
            yield json.dumps(item, default=str) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

@app.get("/api/pdf")
def download_pdf(target: str):
    """
    Serve generated PDF dossier directly in-memory without saving any files to disk.
    """
    clean = target.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Target company name or ticker required.")
    results = supervisor.run_investigation(clean)
    pdf_bytes = results.get("pdf_bytes")
    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={clean}_dossier.pdf"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
