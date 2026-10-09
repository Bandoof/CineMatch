"""Launch the local app independently of the terminal and check readiness."""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8501"


def healthy():
    try:
        with urllib.request.urlopen(URL + "/_stcore/health", timeout=2) as response:
            return response.status == 200 and response.read(32).strip() == b"ok"
    except (OSError, urllib.error.URLError):
        return False


def main(open_browser=True):
    if not healthy():
        # Never terminate another application that owns the requested port.
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8501)) == 0:
                raise RuntimeError("Port 8501 is occupied. See the README troubleshooting instructions.")
        runtime = ROOT / "data" / "runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment["OPENBLAS_NUM_THREADS"] = "1"
        environment["PYTHONUNBUFFERED"] = "1"
        options = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
        with (runtime / "server.log").open("ab") as output:
            process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
                 "--server.address=127.0.0.1", "--server.port=8501",
                 "--browser.gatherUsageStats=false"],
                cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT, **options)
        (runtime / "server.pid").write_text(str(process.pid), encoding="ascii")
        deadline = time.monotonic() + 30
        while not healthy():
            if process.poll() is not None:
                raise RuntimeError(f"CineMatch stopped. Read {runtime / 'server.log'}")
            if time.monotonic() >= deadline:
                raise RuntimeError(f"CineMatch did not become ready. Read {runtime / 'server.log'}")
            time.sleep(.4)
    print(f"CineMatch is ready: {URL}")
    if open_browser:
        webbrowser.open(URL)


if __name__ == "__main__":
    try:
        main(open_browser="--no-browser" not in sys.argv)
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
