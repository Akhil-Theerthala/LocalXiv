#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
port=8765
# A release uses only its own tools plus macOS system tools.
if [ -f "release-id.txt" ] || [ -d "../runtime" ]; then
  # Session discovery uses session.json, so a release need not reserve port 8765.
  port=0
  unset PYTHONHOME PYTHONPATH PYTHONSTARTUP PYTHONUSERBASE NODE_PATH NODE_OPTIONS PERL5LIB PERLLIB PERL5OPT
  unset DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH DYLD_INSERT_LIBRARIES
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  if [ ! -x "../runtime/bin/python3" ]; then
    echo 'The LocalXiv runtime is incomplete. Reinstall LocalXiv.' >&2
    exit 1
  fi
  export PATH="$(cd ../runtime && pwd)/bin:/usr/bin:/bin:/usr/sbin:/sbin"
else
  # Finder does not inherit a development installation's Homebrew paths.
  export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/TeX/texbin:$PATH"
  if ! command -v node >/dev/null 2>&1; then
    for node_bin in "$HOME"/.nvm/versions/node/*/bin; do
      if [ -x "$node_bin/node" ]; then export PATH="$node_bin:$PATH"; fi
    done
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    osascript -e 'display alert "Python 3 is required" message "Install Python 3, then open LocalXiv again."' || true
    exit 1
  fi
fi
if [ "${1:-}" = "--serve" ]; then
  shift
else
  set -- --open "$@"
fi
exec python3 -m app.server --port "$port" --data-dir "$HOME/Library/Application Support/LocalXiv/library" "$@"
