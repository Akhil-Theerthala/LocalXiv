#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
# Finder does not inherit a shell's Homebrew paths.
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/TeX/texbin:$PATH"
# A user may already have Node through nvm rather than Homebrew.
if ! command -v node >/dev/null 2>&1; then
  for node_bin in "$HOME"/.nvm/versions/node/*/bin; do
    if [ -x "$node_bin/node" ]; then export PATH="$node_bin:$PATH"; fi
  done
fi
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "Python 3 is required" message "Install Python 3, then open LocalXiv again."' || true
  exit 1
fi
if [ "${1:-}" = "--serve" ]; then
  shift
else
  set -- --open "$@"
fi
exec python3 -m app.server --port 8765 --data-dir "$HOME/Library/Application Support/LocalXiv/library" "$@"
