#!/bin/bash
# Double-click to start the Product Workbench (macOS Terminal opens and runs this).
# Opens http://127.0.0.1:5173 in your browser once the servers are ready.
# To stop: press Ctrl-C, or close this Terminal window.
# Kept bash 3.2 compatible (macOS /bin/bash).

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/mac_env.sh
. "$ROOT/scripts/mac_env.sh"

FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
export FRONTEND_PORT BACKEND_PORT
URL="http://127.0.0.1:$FRONTEND_PORT"

say() { echo "==> $*"; }
finish() {
  echo
  say "$1"
  say "You can close this window."
  exit "${2:-0}"
}

open_url() {
  if command -v open >/dev/null 2>&1; then
    open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1
  else
    say "Open $1 in your browser."
  fi
}

responds() { curl -fsS -o /dev/null --max-time 2 "$1" 2>/dev/null; }

# Who is listening on a TCP port (empty if nobody).
port_owner() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | awk 'NR == 2 {print $1 " (process " $2 ")"}'
}

# Setup must have been run once.
if [ ! -x "$ROOT/backend/.venv/bin/python" ] || [ ! -x "$ROOT/frontend/node_modules/.bin/vite" ]; then
  say "The workbench hasn't been set up on this Mac yet."
  printf "==> Run the setup now? It asks before installing anything. [Y/n] "
  read -r reply || reply="n"
  case "$reply" in
    n|N|no|NO) finish "Not started. Run setup with: bash scripts/setup_mac.sh" 1 ;;
  esac
  bash "$ROOT/scripts/setup_mac.sh" || finish "Setup did not finish, so the workbench was not started." 1
fi

# Stop whatever listens on a TCP port (asks politely, then insists after 10 s).
stop_port() {
  pids="$(lsof -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null)"
  [ -n "$pids" ] || return 0
  # shellcheck disable=SC2086  # one PID per word
  kill -TERM $pids 2>/dev/null
  for _ in $(seq 1 20); do
    [ -z "$(port_owner "$1")" ] && return 0
    sleep 0.5
  done
  # shellcheck disable=SC2086
  kill -KILL $pids 2>/dev/null
  sleep 0.5
}

# Already running (e.g. in another window)? Just open it, unless that server is still running the code
# from before an update (it loads its code only at start-up, so CAD would be built with the old version;
# a server from before this check doesn't report "stale" at all): then restart it.
health="$(curl -fsS --max-time 2 "http://127.0.0.1:$BACKEND_PORT/api/health" 2>/dev/null)"
if [ -n "$health" ] && responds "$URL/"; then
  case "$health" in
    *'"stale":false'*)
      say "The workbench is already running in another window. Opening $URL"
      open_url "$URL"
      exit 0
      ;;
  esac
  say "The workbench is already running in another window, but with the code from before your last update."
  say "Restarting it so the update takes effect (the other window will say it has stopped)."
  stop_port "$BACKEND_PORT"
  stop_port "$FRONTEND_PORT"
fi

# Anything else on our ports?
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  owner="$(port_owner "$port")"
  if [ -n "$owner" ]; then
    say "Port $port is already in use by $owner, so the workbench can't start."
    say "Close that program (or another Terminal window running the workbench) and try again."
    say "To force it to stop, run: kill \$(lsof -t -iTCP:$port -sTCP:LISTEN)"
    finish "Not started." 1
  fi
done

# Open the browser once both servers answer (in the background).
(
  for _ in $(seq 1 240); do
    if responds "http://127.0.0.1:$BACKEND_PORT/api/health" && responds "$URL/"; then
      say "Ready. Opening $URL in your browser."
      say "To stop the workbench, press Ctrl-C or close this window."
      open_url "$URL"
      exit 0
    fi
    sleep 0.5
  done
  say "The servers are taking a long time to start; check the messages above."
) &
OPENER_PID=$!

# Run run.sh in the background and forward Ctrl-C (INT), a closed Terminal window
# (HUP) and TERM to it as TERM, which run.sh treats as a clean stop of both servers.
# (A background run.sh ignores INT itself, so Ctrl-C is never handled twice.)
STOP_REQUESTED=0
"$ROOT/run.sh" &
RUN_PID=$!
# shellcheck disable=SC2329  # invoked by trap
request_stop() {
  STOP_REQUESTED=1
  kill -TERM "$RUN_PID" 2>/dev/null
}
trap request_stop INT HUP TERM
status=0
while :; do
  wait "$RUN_PID"
  status=$?
  kill -0 "$RUN_PID" 2>/dev/null || break  # still running: wait was interrupted by a signal
done
kill "$OPENER_PID" 2>/dev/null
wait "$OPENER_PID" 2>/dev/null
# After a stop request, run.sh exits 0; a status seen by an interrupted wait is not its own.
[ "$STOP_REQUESTED" = 1 ] && status=0

if [ "$status" = 0 ]; then
  finish "The workbench has stopped."
else
  finish "The workbench stopped because of an error (status $status). See the messages above." "$status"
fi
