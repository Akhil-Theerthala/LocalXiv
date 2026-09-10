#!/bin/bash
set -euo pipefail
source_dir="$(cd "$(dirname "$0")" && pwd)"
install_root="${PAPERS_INSTALL_ROOT:-$HOME/Library/Application Support/LocalXiv}"
applications_dir="${PAPERS_APPLICATIONS_DIR:-$HOME/Applications}"
bundle="$applications_dir/LocalXiv.app"
# Build before replacing the installed launcher, so a compiler failure leaves it usable.
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
xcrun swiftc -module-cache-path "$build_dir/cache" -target "$(uname -m)-apple-macosx11.3" -O \
  "$source_dir/app/macos/PapersToKindle.swift" -o "$build_dir/PapersToKindle"
xcrun swiftc -module-cache-path "$build_dir/cache" -O \
  "$source_dir/papers/HTMLSnapshot.swift" -o "$build_dir/html-snapshot"
python3 -m pip install --target "$build_dir/python-packages" -r "$source_dir/requirements-ai.txt"
# Move the old library once, only while its service is stopped. Never merge libraries.
if [ -z "${PAPERS_INSTALL_ROOT:-}" ]; then
python3 - "$HOME/Library/Application Support/PapersToKindle/library" "$install_root/library" <<'MIGRATE'
import fcntl, sys
from pathlib import Path
old, new = map(Path, sys.argv[1:])
if old.is_dir() and not new.exists():
    with (old / 'server.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Stop the Papers to Kindle background service, then run this installer again. Your library has not been moved.')
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        (new / 'session.json').unlink(missing_ok=True)
        print(f'Moved existing library to {new}')
MIGRATE
fi
mkdir -p "$install_root/app" "$bundle/Contents/MacOS" "$bundle/Contents/Resources"
# Copy only runtime files. The library lives outside this replaceable code directory.
for directory in app papers native; do
  if [ -d "$source_dir/$directory" ]; then
    /usr/bin/rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude 'prototypes/' "$source_dir/$directory" "$install_root/app/"
  fi
done
cp "$build_dir/html-snapshot" "$install_root/app/papers/html-snapshot"
/usr/bin/rsync -a --delete "$build_dir/python-packages/" "$install_root/app/python-packages/"
if [ -f "$source_dir/package.json" ]; then
  cp "$source_dir/package.json" "$source_dir/package-lock.json" "$install_root/app/"
  if [ -d "$source_dir/node_modules" ]; then
    /usr/bin/rsync -a "$source_dir/node_modules" "$install_root/app/"
  else
    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
    (cd "$install_root/app" && npm ci --ignore-scripts --omit=dev)
  fi
fi
cp "$source_dir/launch.command" "$install_root/app/launch.command"
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>LocalXiv</string><key>CFBundleDisplayName</key><string>LocalXiv</string><key>CFBundleIdentifier</key><string>local.paperstokindle.reader</string><key>CFBundleVersion</key><string>1</string><key>CFBundlePackageType</key><string>APPL</string><key>CFBundleExecutable</key><string>PapersToKindle</string></dict></plist>
PLIST
python3 - "$bundle/Contents/Info.plist" "$install_root" <<'PY'
import plistlib, sys
from pathlib import Path
path, root = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
with path.open('rb') as stream: info = plistlib.load(stream)
info.update(CFBundleVersion='3', CFBundleIconFile='AppIcon', NSHighResolutionCapable=True, LSMinimumSystemVersion='11.3',
            PapersRuntimePath=str(root/'app'), PapersDataPath=str(root/'library'),
            NSAppTransportSecurity={'NSAllowsLocalNetworking': True})
with path.open('wb') as stream: plistlib.dump(info, stream)
PY
cp "$source_dir/app/assets/AppIcon.icns" "$bundle/Contents/Resources/AppIcon.icns"
cp "$build_dir/PapersToKindle" "$bundle/Contents/MacOS/PapersToKindle"
chmod +x "$bundle/Contents/MacOS/PapersToKindle" "$install_root/app/launch.command"
codesign --force --sign - "$bundle"
printf 'Installed %s\nLibrary: %s\n' "$bundle" "$install_root/library"
