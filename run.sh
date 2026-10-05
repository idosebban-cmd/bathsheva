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

trap 'kill 0' EXIT INT TERM
(cd "$ROOT/backend" && "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT:-8000}") &
(cd "$ROOT/frontend" && npx vite --host 127.0.0.1 --port "${FRONTEND_PORT:-5173}" --strictPort) &
echo "==> Open http://127.0.0.1:${FRONTEND_PORT:-5173}"
wait
