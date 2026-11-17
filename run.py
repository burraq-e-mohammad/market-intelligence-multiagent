import subprocess
import sys
import time
import argparse
import os

def run_backend():
    print("🚀 Starting FastAPI Backend at http://127.0.0.1:8000...")
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.api:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])

def run_frontend():
    print("🌐 Starting Streamlit Dashboard at http://localhost:8501...")
    return subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.headless", "true"])

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Market Intelligence Launcher")
    parser.add_argument("--backend-only", action="store_true", help="Launch only FastAPI backend")
    parser.add_argument("--frontend-only", action="store_true", help="Launch only Streamlit dashboard")
    args = parser.parse_args()

    processes = []

    try:
        if args.backend_only:
            p_back = run_backend()
            processes.append(p_back)
            p_back.wait()
        elif args.frontend_only:
            p_front = run_frontend()
            processes.append(p_front)
            p_front.wait()
        else:
            p_back = run_backend()
            processes.append(p_back)
            time.sleep(2) # Give FastAPI a moment to bind
            p_front = run_frontend()
            processes.append(p_front)
            print("\n✨ System Online!")
            print("  -> FastAPI Swagger Docs: http://127.0.0.1:8000/docs")
            print("  -> Streamlit Dashboard:  http://localhost:8501")
            print("\nPress Ctrl+C to stop both servers.\n")
            p_front.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        for p in processes:
            p.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
