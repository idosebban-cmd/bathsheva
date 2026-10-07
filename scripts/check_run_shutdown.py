"""Check run.sh start/stop behaviour.

Usage: backend/.venv/bin/python scripts/check_run_shutdown.py

Each scenario starts run.sh (or the macOS launcher "Start Workbench.command") in
a new session, stops it a different way, and checks the exit status and that no
server process is left behind.
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


def cmdline(pid: int) -> bytes:
    """A process's command line, or b"" if it has already exited (short-lived probes do)."""
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return b""


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # Zombies count as gone.
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except OSError:
        return False


RUN_SH = str(ROOT / "run.sh")
LAUNCHER = str(ROOT / "Start Workbench.command")


def scenario(name: str, stop, expected: int, command: str = RUN_SH) -> bool:
    log = tempfile.NamedTemporaryFile(prefix="run_sh_", suffix=".log", delete=False)
    env = {**os.environ, "WORKBENCH_DATA_DIR": tempfile.mkdtemp(prefix="run-sh-check-")}
    proc = subprocess.Popen([command], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
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
        "backend": next(p for p in tree if b"uvicorn" in cmdline(p)),
        "frontend": next(p for p in tree if b"vite" in cmdline(p) and b"esbuild" not in cmdline(p)),
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


def health() -> dict:
    import json

    try:
        return json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2).read())
    except Exception:
        return {}


def stale_restart() -> bool:
    """A workbench left running through an update keeps its old code: starting the launcher again restarts it
    (the old run.sh exits cleanly) instead of just reopening it."""
    name = "launcher: restarts a server running code from before an update"
    data = tempfile.mkdtemp(prefix="run-sh-check-")
    env = {**os.environ, "WORKBENCH_DATA_DIR": data}
    log1 = tempfile.NamedTemporaryFile(prefix="run_sh_", suffix=".log", delete=False)
    old = subprocess.Popen([RUN_SH], stdin=subprocess.DEVNULL, stdout=log1, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    for _ in range(240):
        if up("http://127.0.0.1:8000/api/health") and up("http://127.0.0.1:5173/"):
            break
        time.sleep(0.5)
    old_tree = descendants(old.pid)
    marker = ROOT / "backend" / "app" / "_update_marker.tmp"  # stands in for files changed by git pull
    marker.write_text("update\n")
    new = None
    try:
        was_stale = health().get("stale") is True
        log2 = tempfile.NamedTemporaryFile(prefix="run_sh_", suffix=".log", delete=False)
        new = subprocess.Popen([LAUNCHER], stdin=subprocess.DEVNULL, stdout=log2, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        old_status = old.wait(timeout=60)
        for _ in range(240):
            h = health()
            if h.get("stale") is False and up("http://127.0.0.1:5173/"):
                break
            time.sleep(0.5)
        restarted = health().get("stale") is False
        new_tree = descendants(new.pid)
        os.killpg(new.pid, signal.SIGINT)
        new_status = new.wait(timeout=30)
    finally:
        marker.unlink(missing_ok=True)
        if new and new.poll() is None:
            os.killpg(new.pid, signal.SIGKILL)
    time.sleep(0.5)
    left = [p for p in old_tree + new_tree if alive(p)]
    ok = was_stale and old_status == 0 and restarted and new_status == 0 and not left
    print(f"{'PASS' if ok else 'FAIL'} {name}: stale before {was_stale}, old run.sh exit {old_status}, "
          f"restarted on current code {restarted}, launcher exit {new_status}, leftover processes: {left or 'none'}")
    print("     launcher said:", next((ln for ln in Path(log2.name).read_text().splitlines() if "before your last update" in ln), "?"))
    for p in left:
        os.kill(p, signal.SIGKILL)
    return ok


def main() -> int:
    results = [
        scenario("SIGTERM to run.sh", lambda proc, s: proc.send_signal(signal.SIGTERM), 0),
        scenario("SIGINT to run.sh (Ctrl-C)", lambda proc, s: os.killpg(proc.pid, signal.SIGINT), 0),
        scenario("servers killed externally", lambda proc, s: [os.kill(p, signal.SIGTERM) for p in s.values()], 0),
        scenario("backend crashes (SIGSEGV)", lambda proc, s: os.kill(s["backend"], signal.SIGSEGV), 139),
        scenario("SIGHUP to the group (Terminal window closed)", lambda proc, s: os.killpg(proc.pid, signal.SIGHUP), 0),
        scenario("launcher: Ctrl-C", lambda proc, s: os.killpg(proc.pid, signal.SIGINT), 0, LAUNCHER),
        scenario("launcher: Terminal window closed", lambda proc, s: os.killpg(proc.pid, signal.SIGHUP), 0, LAUNCHER),
        scenario("launcher: SIGHUP to the launcher only", lambda proc, s: proc.send_signal(signal.SIGHUP), 0, LAUNCHER),
        scenario("launcher: backend crashes", lambda proc, s: os.kill(s["backend"], signal.SIGSEGV), 139, LAUNCHER),
        stale_restart(),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
