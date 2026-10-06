#!/usr/bin/env bash
# One-time (and safe to re-run) setup of the Product Workbench on a Mac.
#
#   bash scripts/setup_mac.sh            check, ask before installing anything, set up
#   bash scripts/setup_mac.sh --yes      same, answering "yes" to every question
#   bash scripts/setup_mac.sh --dry-run  only report what would be done; changes nothing
#
# It installs (asking first) the Xcode command line tools, Homebrew, uv and
# Node.js LTS if they are missing, creates backend/.venv with a pinned Python,
# installs dependencies, updates the database and generates the Faro lamp once
# as a self-test.
#
# WORKBENCH_SETUP_ALLOW_NON_MAC=1 runs the non-macOS parts on Linux (for testing).
# Kept bash 3.2 compatible (macOS /bin/bash).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/backend/.venv"
PY="$VENV/bin/python"
# build123d (OpenCASCADE) has prebuilt wheels for Python 3.12 on both Apple Silicon and Intel Macs (macOS 12+).
PYTHON_VERSION="3.12"
MIN_NODE_MAJOR=18
TOTAL_STEPS=7

YES=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) YES=1 ;;
    -n|--dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

IS_MAC=0
[ "$(uname -s)" = "Darwin" ] && IS_MAC=1
if [ "$IS_MAC" = 0 ] && [ "${WORKBENCH_SETUP_ALLOW_NON_MAC:-}" != 1 ]; then
  echo "This script is for macOS. On Linux, use ./run.sh." >&2
  exit 1
fi

# Keep a log of the whole run (not in dry-run mode, which changes nothing): re-run
# this script through tee. A pipeline (not `exec > >(tee)`) so bash waits for tee
# and the final message is never lost or printed after the prompt.
if [ "$DRY_RUN" = 0 ] && [ -z "${WORKBENCH_SETUP_LOG:-}" ]; then
  LOG_DIR="$HOME/Bathsheva Workbench/logs"
  mkdir -p "$LOG_DIR"
  WORKBENCH_SETUP_LOG="$LOG_DIR/setup.log"
  WORKBENCH_SETUP_COLOR=0
  [ -t 1 ] && WORKBENCH_SETUP_COLOR=1
  export WORKBENCH_SETUP_LOG WORKBENCH_SETUP_COLOR
  set +e
  /bin/bash "$0" "$@" 2>&1 | tee "$WORKBENCH_SETUP_LOG"
  exit "${PIPESTATUS[0]}"
fi
LOG_FILE="${WORKBENCH_SETUP_LOG:-}"

if [ "${WORKBENCH_SETUP_COLOR:-}" = 1 ] || { [ -z "${WORKBENCH_SETUP_COLOR:-}" ] && [ -t 1 ]; }; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; RED=""; YELLOW=""; RESET=""
fi

# --- output helpers -----------------------------------------------------------

STEP_NO=0
STEP_NAME="starting"
HINT=""

step() {
  STEP_NO=$((STEP_NO + 1))
  STEP_NAME="$1"
  HINT=""
  echo
  echo "${BOLD}Step $STEP_NO of $TOTAL_STEPS: $1${RESET}"
}
ok()   { echo "  ${GREEN}✓${RESET} $*"; }
info() { echo "    $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }

# Run a command, or only print it in dry-run mode.
run() {
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry run] would run: $*"
  else
    "$@"
  fi
}

# Ask a yes/no question. Returns 0 for yes.
ask() {
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry run] would ask: $1 (assuming yes)"
    return 0
  fi
  if [ "$YES" = 1 ]; then
    echo "    $1 yes (--yes)"
    return 0
  fi
  if [ ! -t 0 ]; then
    echo "    $1 (no keyboard to answer; re-run in Terminal, or with --yes)" >&2
    return 1
  fi
  local reply
  printf "    %s [y/N] " "$1"
  read -r reply || reply=""
  case "$reply" in
    y|Y|yes|YES|Yes) return 0 ;;
    *) return 1 ;;
  esac
}

# Stop with a plain-English reason (the EXIT trap prints the summary).
fail() {
  echo "  ${RED}✗${RESET} $*" >&2
  exit 1
}

on_exit() {
  local status=$?
  trap - EXIT
  echo
  if [ "$status" = 0 ]; then
    if [ "$DRY_RUN" = 1 ]; then
      echo "${BOLD}Dry run finished. Nothing was changed.${RESET} Run without --dry-run to set up."
    else
      echo "${GREEN}${BOLD}Setup finished successfully.${RESET}"
      echo "Start the workbench by double-clicking \"Start Workbench.command\" in the bathsheva folder."
      echo "Your projects are kept in: ${DATA_DIR_SHOWN:-~/Bathsheva Workbench/data}"
    fi
  else
    echo "${RED}${BOLD}Setup did not finish.${RESET} It stopped at step $STEP_NO ($STEP_NAME)." >&2
    [ -n "$HINT" ] && echo "What to try: $HINT" >&2
    echo "It is safe to run this script again; it picks up where it left off." >&2
    [ -n "${LOG_FILE:-}" ] && echo "A full log is in: $LOG_FILE" >&2
  fi
  exit "$status"
}
trap on_exit EXIT

echo "${BOLD}Product Workbench setup${RESET}  ($(date '+%Y-%m-%d %H:%M'))"
echo "Folder: $ROOT"
[ "$DRY_RUN" = 1 ] && echo "${YELLOW}Dry run: nothing will be installed or changed.${RESET}"

# shellcheck source=scripts/mac_env.sh
. "$ROOT/scripts/mac_env.sh"

# --- 1. macOS and Xcode command line tools -----------------------------------

step "Xcode command line tools"
if [ "$IS_MAC" = 1 ]; then
  macos_version="$(sw_vers -productVersion)"
  macos_major="${macos_version%%.*}"
  if [ "$macos_major" -lt 12 ]; then
    HINT="The CAD kernel needs macOS 12 (Monterey) or newer. Update macOS in System Settings."
    fail "This Mac runs macOS $macos_version, which is too old."
  fi
  ok "macOS $macos_version on $(uname -m)"
  if xcode-select -p >/dev/null 2>&1; then
    ok "Already installed"
  else
    info "Apple's command line tools (git, compilers) are needed by Homebrew."
    HINT="Install them yourself with: xcode-select --install"
    ask "Install the Xcode command line tools now? (Apple's installer window will open)" \
      || fail "The Xcode command line tools are required."
    run xcode-select --install || true
    if [ "$DRY_RUN" = 0 ]; then
      info "Click \"Install\" in the window that opened and wait for it to finish."
      info "Waiting for the installation to complete..."
      waited=0
      until xcode-select -p >/dev/null 2>&1; do
        sleep 5
        waited=$((waited + 5))
        [ "$waited" -ge 3600 ] && fail "Gave up waiting after an hour."
      done
      ok "Installed"
    fi
  fi
else
  warn "Not a Mac: skipped (WORKBENCH_SETUP_ALLOW_NON_MAC=1)"
fi

# --- 2. Homebrew (only needed if uv or Node.js is missing) --------------------

node_major() {
  command -v node >/dev/null 2>&1 || { echo 0; return; }
  local v
  v="$(node --version 2>/dev/null || echo v0)"
  v="${v#v}"
  echo "${v%%.*}"
}

need_uv=0
need_node=0
command -v uv >/dev/null 2>&1 || need_uv=1
[ "$(node_major)" -ge "$MIN_NODE_MAJOR" ] || need_node=1

step "Homebrew"
if [ "$need_uv" = 0 ] && [ "$need_node" = 0 ]; then
  ok "Not needed (uv and Node.js are already installed)"
elif command -v brew >/dev/null 2>&1; then
  ok "Already installed ($(brew --version | head -n 1))"
elif [ "$IS_MAC" = 0 ]; then
  HINT="Install uv (https://docs.astral.sh/uv/) and Node.js $MIN_NODE_MAJOR+ yourself."
  fail "uv or Node.js is missing, and Homebrew installs are only done on macOS."
else
  info "Homebrew (https://brew.sh) is the standard way to install developer tools on a Mac."
  info "Its installer will ask for your Mac login password."
  HINT="Install Homebrew yourself from https://brew.sh, then run this script again."
  ask "Install Homebrew now?" || fail "Homebrew is needed to install uv and Node.js."
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry run] would run the official installer from https://brew.sh"
  else
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # shellcheck source=scripts/mac_env.sh
    . "$ROOT/scripts/mac_env.sh"
    command -v brew >/dev/null 2>&1 || fail "Homebrew installed, but 'brew' can't be found."
    ok "Installed"
  fi
fi

# --- 3. uv and Node.js --------------------------------------------------------

step "uv (Python manager) and Node.js"
if [ "$need_uv" = 0 ]; then
  ok "uv $(uv --version | awk '{print $2}')"
else
  HINT="Run: brew install uv"
  ask "Install uv with Homebrew?" || fail "uv is required to set up Python."
  run brew install uv
  [ "$DRY_RUN" = 1 ] || ok "uv installed"
fi
if [ "$need_node" = 0 ]; then
  ok "Node.js $(node --version)"
else
  if command -v node >/dev/null 2>&1; then
    info "Node.js $(node --version) is too old; version $MIN_NODE_MAJOR or newer is needed."
  fi
  HINT="Run: brew install $WORKBENCH_NODE_FORMULA"
  ask "Install Node.js LTS ($WORKBENCH_NODE_FORMULA) with Homebrew?" || fail "Node.js is required for the web interface."
  run brew install "$WORKBENCH_NODE_FORMULA"
  if [ "$DRY_RUN" = 0 ]; then
    # shellcheck source=scripts/mac_env.sh
    . "$ROOT/scripts/mac_env.sh"
    [ "$(node_major)" -ge "$MIN_NODE_MAJOR" ] || fail "Node.js installed, but the right version can't be found."
    ok "Node.js $(node --version) installed"
  fi
fi

# --- 4. Python environment and backend packages ------------------------------

step "Python $PYTHON_VERSION and backend packages (the CAD kernel is large; the first run takes a few minutes)"
HINT="Check your internet connection and run the script again. If the CAD kernel keeps failing, see Troubleshooting in README.md."
have_py=""
if [ -x "$PY" ]; then
  have_py="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
fi
if [ "$have_py" = "$PYTHON_VERSION" ]; then
  ok "Python environment exists (backend/.venv, Python $have_py)"
else
  if [ -e "$VENV" ]; then
    info "backend/.venv uses Python ${have_py:-unknown}; recreating it with Python $PYTHON_VERSION."
    run rm -rf "$VENV"
  fi
  run uv venv --quiet --python "$PYTHON_VERSION" --python-preference only-managed "$VENV"
  [ "$DRY_RUN" = 1 ] || ok "Created backend/.venv with Python $PYTHON_VERSION"
fi
# The CAD kernel moved from CadQuery to build123d. Both ship an OCP module, and removing
# CadQuery's deletes files build123d's package shares, so that one is reinstalled after.
OCP_PKGS="cadquery-ocp-novtk cadquery-ocp-proxy"
repair_ocp() {
  # shellcheck disable=SC2086  # word splitting of the package list is intended
  run uv pip install --quiet --python "$PY" --reinstall $OCP_PKGS
}
had_cadquery=0
if [ -x "$PY" ] && "$PY" -c "import cadquery" >/dev/null 2>&1; then
  info "Removing CadQuery (replaced by build123d)."
  run uv pip uninstall --quiet --python "$PY" cadquery cadquery-ocp cadquery-ocp-proxy
  had_cadquery=1
fi
run uv pip install --quiet --python "$PY" -e "$ROOT/backend[dev]"
[ "$had_cadquery" = 1 ] && repair_ocp
if [ "$DRY_RUN" = 0 ] && ! "$PY" -c "import build123d" >/dev/null 2>&1; then
  info "Repairing the CAD kernel install."
  repair_ocp
fi
if [ "$DRY_RUN" = 0 ]; then
  "$PY" -c "import build123d, fastapi, alembic" || fail "The backend packages did not install correctly."
  ok "Backend packages installed (build123d $("$PY" -c 'import build123d; print(build123d.__version__)'))"
fi

# --- 5. Front-end packages ---------------------------------------------------

step "Front-end packages"
HINT="Check your internet connection and run the script again."
FE="$ROOT/frontend"
if [ -f "$FE/node_modules/.package-lock.json" ] && [ ! "$FE/package-lock.json" -nt "$FE/node_modules/.package-lock.json" ] \
  && [ -x "$FE/node_modules/.bin/vite" ]; then
  ok "Already up to date"
else
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry run] would run: npm ci (in frontend/)"
  else
    (cd "$FE" && npm ci --no-audit --no-fund --no-update-notifier --loglevel=error)
    ok "Installed"
  fi
fi

# --- 6. Data folder and database ---------------------------------------------

step "Your data folder and database"
HINT="Your data has not been deleted. Send the log file below to whoever maintains the workbench."
if [ "$DRY_RUN" = 1 ]; then
  info "Data folder: ${WORKBENCH_DATA_DIR:-$HOME/Bathsheva Workbench/data}"
  for legacy in "$ROOT/data" "$ROOT/backend/data"; do
    if [ -d "$legacy" ] && [ -n "$(ls -A "$legacy" 2>/dev/null)" ]; then
      echo "    [dry run] would move old data from $legacy to the data folder (if that folder is empty)"
    fi
  done
  echo "    [dry run] would back up the database (if it needs updating) and update it"
else
  "$PY" "$ROOT/scripts/workbench_check.py" migrate
  DATA_DIR_SHOWN="$(cd "$ROOT/backend" && "$PY" -c 'from app.config import settings; print(settings.data_dir)')"
  ok "Database ready"
fi

# Double-clicking needs the launcher to be executable and not quarantined
# (a ZIP download from the browser marks files as quarantined).
for f in "$ROOT/Start Workbench.command" "$ROOT/run.sh"; do
  [ -f "$f" ] || continue
  [ -x "$f" ] || run chmod +x "$f"
  if [ "$IS_MAC" = 1 ] && xattr -p com.apple.quarantine "$f" >/dev/null 2>&1; then
    run xattr -d com.apple.quarantine "$f"
  fi
done

# --- 7. Self-test ------------------------------------------------------------

step "Self-test (generates the Faro lamp CAD once, in a temporary folder)"
HINT="The install looks broken. Delete the backend/.venv folder and run this script again."
if [ "$DRY_RUN" = 1 ]; then
  echo "    [dry run] would run: scripts/workbench_check.py selftest"
else
  "$PY" "$ROOT/scripts/workbench_check.py" selftest
  ok "Self-test passed"
fi
