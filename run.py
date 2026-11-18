import subprocess
import sys
import time
import argparse
import os
import re

def free_port(port: int):
    """Terminate any stale process currently listening on the given port (Windows/Unix)."""
    try:
        if os.name == "nt":
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
            )
            pids = set()
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line.upper():
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        if pid > 0 and pid != os.getpid():
                            pids.add(pid)
            for pid in pids:
                print(f"🧹 Clearing stale process (PID {pid}) on port {port}...")
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F", "/T"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            if pids:
                time.sleep(1)
        else:
            out = subprocess.check_output(
                ["lsof", "-ti", f"tcp:{port}"], text=True, stderr=subprocess.DEVNULL
            )
            for line in out.splitlines():
                if line.strip().isdigit():
                    subprocess.run(["kill", "-9", line.strip()], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def run_backend():
    free_port(8000)
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
