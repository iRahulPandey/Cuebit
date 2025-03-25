# cuebit/cli.py
import uvicorn
import argparse
import subprocess
import os
import threading

def start_streamlit():
    dashboard_path = os.path.join(os.path.dirname(__file__), "../cuebit_dashboard.py")
    subprocess.Popen(["streamlit", "run", dashboard_path])

def main():
    parser = argparse.ArgumentParser(description="Start Cuebit backend and UI")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Start Streamlit in background
    threading.Thread(target=start_streamlit, daemon=True).start()

    # Start FastAPI
    uvicorn.run("cuebit.server:app", host=args.host, port=args.port, reload=True)
