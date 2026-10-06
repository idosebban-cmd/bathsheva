"""Stress test: many CAD regenerations + downloads in one running backend, then shutdown.

Usage: backend/.venv/bin/python scripts/stress_cad.py [N] [SIGNAL]
Reports HTTP failures, whether the server process survived, and its exit code after SIGNAL.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
SIG = getattr(signal, sys.argv[2]) if len(sys.argv) > 2 else signal.SIGTERM
PORT = 8019
BASE = f"http://127.0.0.1:{PORT}"
BACKEND = Path(__file__).resolve().parent.parent / "backend"


def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = r.read()
        return payload if raw else json.loads(payload)


def main():
    try:
        call("GET", "/api/health")
        print(f"port {PORT} is already in use; stop the other server first"); sys.exit(2)
    except Exception:
        pass
    env = {**os.environ, "WORKBENCH_DATA_DIR": tempfile.mkdtemp(prefix="stress-"), "WORKBENCH_LLM_PROVIDER": "none"}
    # Log to a file: an unread pipe fills up and blocks the server's logging.
    log = tempfile.NamedTemporaryFile(prefix="stress-uvicorn-", suffix=".log", delete=False)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    for _ in range(120):
        try:
            call("GET", "/api/health")
            break
        except Exception:
            time.sleep(0.25)
    else:
        print("server did not start"); proc.kill(); sys.exit(2)

    pid = call("POST", "/api/projects", {"name": "Faro", "template": "faro"})["id"]
    params = call("GET", f"/api/projects/{pid}/cad")["parameters"]
    failures = 0
    t0 = time.time()
    for i in range(N):
        p = {**params, "overall_height": 280 + (i % 20) * 10, "wall_thickness": 1.2 + (i % 3) * 0.3}
        try:
            model = call("POST", f"/api/projects/{pid}/cad/generate", {"parameters": p})
            for out in model["outputs"]:
                call("GET", "/files/" + out["path"], raw=True)
            call("GET", f"/api/projects/{pid}/cad/models/{model['version']}/download.zip", raw=True)
        except Exception as e:
            failures += 1
            print(f"iteration {i}: {e!r}", flush=True)
        if proc.poll() is not None:
            print(f"SERVER DIED during iteration {i} with code {proc.returncode}")
            break
    alive = proc.poll() is None
    print(f"{N} regenerations in {time.time() - t0:.1f}s, failures={failures}, server alive={alive}")
    if alive:
        proc.send_signal(SIG)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print("server did not stop in 30s"); proc.kill()
    print(f"exit code after {SIG.name}: {proc.returncode}")
    tail = Path(log.name).read_text().strip().splitlines()[-3:]
    print("log tail:", *tail, sep="\n  ")
    sys.exit(0 if alive and failures == 0 and proc.returncode in (0, -SIG.value) else 1)


if __name__ == "__main__":
    main()
