#!/bin/bash
set -euo pipefail

EXTENSION_ID=${1:-}
if [[ ! $EXTENSION_ID =~ ^[a-p]{32}$ ]]; then
  echo "Usage: ./install.sh <32-character Chrome extension ID>" >&2
  exit 2
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON_BIN=$(command -v python3 || true)
PANDOC_BIN=$(command -v pandoc || true)
FOREST_TEX_BIN=$(command -v pdflatex || command -v xelatex || true)
if [[ -z $PANDOC_BIN && -x /opt/homebrew/bin/pandoc ]]; then PANDOC_BIN=/opt/homebrew/bin/pandoc; fi
if [[ -z $PANDOC_BIN && -x /usr/local/bin/pandoc ]]; then PANDOC_BIN=/usr/local/bin/pandoc; fi
if [[ -z $FOREST_TEX_BIN && -x /Library/TeX/texbin/pdflatex ]]; then FOREST_TEX_BIN=/Library/TeX/texbin/pdflatex; fi
if [[ -z $FOREST_TEX_BIN && -x /Library/TeX/texbin/xelatex ]]; then FOREST_TEX_BIN=/Library/TeX/texbin/xelatex; fi
if [[ -z $PYTHON_BIN ]]; then
  echo "Python 3 is required." >&2
  exit 1
fi
if [[ -z $PANDOC_BIN ]]; then
  echo "Pandoc is required. Install it with: brew install pandoc" >&2
  exit 1
fi

APP_DIR="$HOME/Library/Application Support/ArxivToKindle"
MANIFEST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
HOST_PATH="$APP_DIR/host.py"
MANIFEST_PATH="$MANIFEST_DIR/com.arxiv_to_kindle.host.json"
mkdir -p "$APP_DIR" "$MANIFEST_DIR"
cp "$SCRIPT_DIR/native/host.py" "$HOST_PATH"
/usr/bin/sed -i '' "1s|.*|#!$PYTHON_BIN|" "$HOST_PATH"
chmod 755 "$HOST_PATH"

"$PYTHON_BIN" - "$MANIFEST_PATH" "$HOST_PATH" "$EXTENSION_ID" <<'PY'
import json
import sys

manifest_path, host_path, extension_id = sys.argv[1:]
manifest = {
    "name": "com.arxiv_to_kindle.host",
    "description": "Local arXiv source to Kindle EPUB converter",
    "path": host_path,
    "type": "stdio",
    "allowed_origins": [f"chrome-extension://{extension_id}/"],
}
with open(manifest_path, "w", encoding="utf-8") as output:
    json.dump(manifest, output, indent=2)
    output.write("\n")
PY

echo "Installed native host for extension $EXTENSION_ID"
echo "Pandoc: $PANDOC_BIN"
if [[ -n $FOREST_TEX_BIN ]]; then
  echo "TeX diagram engine: $FOREST_TEX_BIN"
else
  echo "TeX diagram engine: not found (pdfLaTeX or XeLaTeX; only required for in-source forest diagrams)"
fi
echo "Restart Chrome, open an arXiv abstract page, and click the extension."
echo "Optional local library: run ./install-app.sh, then choose 'Import into local library' in the extension."
