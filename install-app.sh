#!/bin/bash
set -euo pipefail
source_dir="$(cd "$(dirname "$0")" && pwd)"
install_root="${PAPERS_INSTALL_ROOT:-$HOME/Library/Application Support/LocalXiv}"
applications_dir="${PAPERS_APPLICATIONS_DIR:-$HOME/Applications}"
bundle="$applications_dir/LocalXiv.app"
# Build before replacing the installed launcher, so a compiler failure leaves it usable.
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
xcrun swiftc -module-cache-path "$build_dir/cache" -target "$(uname -m)-apple-macosx26.0" -O \
  "$source_dir"/app/macos/*.swift -o "$build_dir/PapersToKindle"
xcrun swiftc -module-cache-path "$build_dir/cache" -O \
  "$source_dir/papers/HTMLSnapshot.swift" -o "$build_dir/html-snapshot"
# launch.command runs python3.14 when it exists, so the packages are for its ABI. The newest Homebrew python3 can
# lack wheels that load, such as pydantic_core's. The PATH is launch.command's, so both find the same Python.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
python=python3
if command -v python3.14 >/dev/null 2>&1; then python=python3.14; fi
"$python" -m pip install --target "$build_dir/python-packages" -r "$source_dir/requirements-ai.txt"
mkdir -p "$install_root/app" "$bundle/Contents/MacOS" "$bundle/Contents/Resources"
# Copy only runtime files. The library lives outside this replaceable code directory.
for directory in app papers native; do
  if [ -d "$source_dir/$directory" ]; then
    /usr/bin/rsync -aL --exclude '__pycache__' --exclude '*.pyc' --exclude 'prototypes/' "$source_dir/$directory" "$install_root/app/"
  fi
done
cp "$build_dir/html-snapshot" "$install_root/app/papers/html-snapshot"
/usr/bin/rsync -a --delete "$build_dir/python-packages/" "$install_root/app/python-packages/"
if [ -f "$source_dir/package.json" ]; then
  cp "$source_dir/package.json" "$source_dir/package-lock.json" "$install_root/app/"
  if [ -d "$source_dir/node_modules" ]; then
    /usr/bin/rsync -aL "$source_dir/node_modules" "$install_root/app/"
  else
    (cd "$install_root/app" && npm ci --ignore-scripts --omit=dev)
  fi
fi
cp "$source_dir/launch.command" "$install_root/app/launch.command"
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>LocalXiv</string><key>CFBundleDisplayName</key><string>LocalXiv</string><key>CFBundleIdentifier</key><string>local.paperstokindle.reader</string><key>CFBundleVersion</key><string>1</string><key>CFBundlePackageType</key><string>APPL</string><key>CFBundleExecutable</key><string>PapersToKindle</string></dict></plist>
PLIST
"$python" - "$bundle/Contents/Info.plist" "$install_root" <<'PY'
import plistlib, sys
from pathlib import Path
path, root = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
with path.open('rb') as stream: info = plistlib.load(stream)
info.update(CFBundleVersion='3', CFBundleIconFile='AppIcon', NSHighResolutionCapable=True, LSMinimumSystemVersion='26.0',
            PapersRuntimePath=str(root/'app'), PapersDataPath=str(root/'library'),
            NSAppTransportSecurity={'NSAllowsLocalNetworking': True},
            CFBundleURLTypes=[{'CFBundleURLName': 'local.paperstokindle.reader', 'CFBundleURLSchemes': ['localxiv']}])
with path.open('wb') as stream: plistlib.dump(info, stream)
PY
cp "$source_dir/app/assets/AppIcon.icns" "$bundle/Contents/Resources/AppIcon.icns"
cp "$build_dir/PapersToKindle" "$bundle/Contents/MacOS/PapersToKindle"
chmod +x "$bundle/Contents/MacOS/PapersToKindle" "$install_root/app/launch.command"
codesign --force --sign - "$bundle"
printf 'Installed %s\nLibrary: %s\n' "$bundle" "$install_root/library"
