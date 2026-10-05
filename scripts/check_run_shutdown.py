"""Check run.sh start/stop behaviour.

Usage: backend/.venv/bin/python scripts/check_run_shutdown.py

Each scenario starts run.sh in a new session, stops it a different way, and
checks run.sh's exit status and that no server process is left behind.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def up(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=2).read()
        return True
    except Exception:
        return False


def children(pid: int) -> list[int]:
    out = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def descendants(pid: int) -> list[int]:
    result = []
    for c in children(pid):
        result.append(c)
        result.extend(descendants(c))
    return result


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # Zombies count as gone.
    stat = Path(f"/proc/{pid}/stat")
    return not (stat.exists() and stat.read_text().split()[2] == "Z")


def scenario(name: str, stop, expected: int) -> bool:
    log = tempfile.NamedTemporaryFile(prefix="run_sh_", suffix=".log", delete=False)
    env = {**os.environ, "WORKBENCH_DATA_DIR": tempfile.mkdtemp(prefix="run-sh-check-")}
    proc = subprocess.Popen([str(ROOT / "run.sh")], stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    for _ in range(240):
        if up("http://127.0.0.1:8000/api/health") and up("http://127.0.0.1:5173/"):
            break
        time.sleep(0.5)
    else:
        print(f"FAIL {name}: servers did not start")
        proc.kill()
        return False
    tree = descendants(proc.pid)
    servers = {
        "backend": next(p for p in tree if b"uvicorn" in Path(f"/proc/{p}/cmdline").read_bytes()),
        "frontend": next(p for p in tree if b"vite" in Path(f"/proc/{p}/cmdline").read_bytes() and b"esbuild" not in Path(f"/proc/{p}/cmdline").read_bytes()),
    }
    stop(proc, servers)
    try:
        status = proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        status = None
    time.sleep(0.5)
    left = [p for p in tree if alive(p)]
    output = Path(log.name).read_text()
    ok = status == expected and not left
    print(f"{'PASS' if ok else 'FAIL'} {name}: exit {status} (expected {expected}), leftover processes: {left or 'none'}")
    print("     last line:", output.strip().splitlines()[-1])
    for p in left:
        os.kill(p, signal.SIGKILL)
    return ok


def main() -> int:
    results = [
        scenario("SIGTERM to run.sh", lambda proc, s: proc.send_signal(signal.SIGTERM), 0),
        scenario("SIGINT to run.sh (Ctrl-C)", lambda proc, s: os.killpg(proc.pid, signal.SIGINT), 0),
        scenario("servers killed externally", lambda proc, s: [os.kill(p, signal.SIGTERM) for p in s.values()], 0),
        scenario("backend crashes (SIGSEGV)", lambda proc, s: os.kill(s["backend"], signal.SIGSEGV), 139),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
