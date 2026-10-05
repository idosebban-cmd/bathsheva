#!/usr/bin/env bash
# One command to set up (first run) and start the whole app.
#   ./run.sh          start backend (:8000) and front end (:5173)
#   ./run.sh test     run backend tests and front-end typecheck
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/backend/.venv"
PY="$VENV/bin/python"

setup_backend() {
  if [ ! -x "$PY" ]; then
    echo "==> Creating Python venv (backend/.venv)"
    if command -v uv >/dev/null 2>&1; then
      uv venv -q "$VENV"
    else
      python3 -m venv "$VENV"
    fi
  fi
  if ! "$PY" -c "import cadquery, fastapi, anthropic, pytest" >/dev/null 2>&1; then
    echo "==> Installing backend dependencies (CadQuery is large; first run takes a few minutes)"
    if command -v uv >/dev/null 2>&1; then
      uv pip install -q -p "$PY" -e "$ROOT/backend[dev]"
    else
      "$PY" -m pip install -q -e "$ROOT/backend[dev]"
    fi
  fi
}

setup_frontend() {
  if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "==> Installing front-end dependencies"
    (cd "$ROOT/frontend" && npm install --silent)
  fi
}

setup_backend
setup_frontend

if [ "${1:-}" = "test" ]; then
  (cd "$ROOT/backend" && "$PY" -m pytest -q)
  (cd "$ROOT/frontend" && npm run -s typecheck)
  exit 0
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${WORKBENCH_LLM_PROVIDER:-}" ]; then
  echo "==> ANTHROPIC_API_KEY not set: running with the LLM disabled (rules engine only)"
fi

# Process management. Only our own two servers are signalled (never `kill 0`, which
# would also hit whatever launched this script). Traps reset themselves before
# acting so a signal can't re-enter them. Kept bash 3.2 compatible for macOS.
BACKEND_PID=""
FRONTEND_PID=""

stop_servers() {
  trap - EXIT INT TERM
  for pid in $BACKEND_PID $FRONTEND_PID; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in $BACKEND_PID $FRONTEND_PID; do
    wait "$pid" 2>/dev/null || true
  done
}

on_signal() {
  echo
  echo "==> Stopping"
  stop_servers
  exit 0
}

trap on_signal INT TERM
trap stop_servers EXIT

(cd "$ROOT/backend" && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT:-8000}") &
BACKEND_PID=$!
(cd "$ROOT/frontend" && exec node_modules/.bin/vite --host 127.0.0.1 --port "${FRONTEND_PORT:-5173}" --strictPort) &
FRONTEND_PID=$!
echo "==> Open http://127.0.0.1:${FRONTEND_PORT:-5173}  (Ctrl-C to stop)"

# Run until either server exits (polling keeps this portable to bash 3.2).
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

if kill -0 "$BACKEND_PID" 2>/dev/null; then
  name="front end"; pid=$FRONTEND_PID
else
  name="backend"; pid=$BACKEND_PID
fi
status=0
wait "$pid" || status=$?
stop_servers
# A server stopped by SIGTERM/SIGINT (143/130) or exiting 0 is a normal stop.
case "$status" in
  0|130|143)
    echo "==> The $name stopped; shut down the other server."
    exit 0
    ;;
  *)
    echo "==> The $name exited unexpectedly with status $status; shut down the other server." >&2
    exit "$status"
    ;;
esac
