# Shared environment for scripts/setup_mac.sh and "Start Workbench.command".
# Source it (don't run it). Puts Homebrew, uv and Node.js on PATH even when the
# user's shell profile doesn't, so double-clicking works without shell setup.
# Kept bash 3.2 compatible (macOS /bin/bash).

# Homebrew: /opt/homebrew on Apple Silicon, /usr/local on Intel.
for _brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  if [ -x "$_brew" ]; then
    eval "$("$_brew" shellenv)"
    break
  fi
done
unset _brew

# uv's own installer puts it in ~/.local/bin.
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) [ -d "$HOME/.local/bin" ] && PATH="$HOME/.local/bin:$PATH" ;;
esac

# Homebrew's Node.js LTS formula is keg-only (not linked into brew's bin), so add it.
WORKBENCH_NODE_FORMULA="node@24"
if [ -n "${HOMEBREW_PREFIX:-}" ] && [ -d "$HOMEBREW_PREFIX/opt/$WORKBENCH_NODE_FORMULA/bin" ]; then
  PATH="$HOMEBREW_PREFIX/opt/$WORKBENCH_NODE_FORMULA/bin:$PATH"
fi
export PATH
