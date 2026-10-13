#!/usr/bin/env python3
"""Run the Mac app on a copy of a library, follow a step file, and print the snapshot paths.

  python3 tools/native_shot.py --library DIR --steps STEPS.json --out DIR

The step file is a JSON list. The app runs it in order after the first page load:

  {"js": "..."}                    run JavaScript in the page and log the result
  {"command": {...}}               call window.localxiv.command when it exists
  {"state": {...}}                 give the shell a Chrome state, as if the page posted it
  {"toolbar": "views"}             perform the action of the toolbar item with this identifier
  {"menu": "View/Paper"}           choose a menu item by menu title and item title
  {"wait": 1.5}                    wait this many seconds
  {"size": [1180, 820]}            set the window content size
  {"appearance": "light"}          set the app appearance, "light" or "dark"
  {"snapshot": "name.png"}         write the window, with the page drawn in, into --out
  {"quit": true}                   quit the app

The app, its service, and the library copy live in --out/.scratch, which the next run replaces.
The installed app, its library, and its defaults are not touched. The service is stopped at the end.
"""
import argparse
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def live(library):
    try:
        session = json.loads((library / 'session.json').read_text())
        request = urllib.request.Request(f"http://127.0.0.1:{session['port']}/api/health",
                                         headers={'Authorization': 'Bearer ' + session['token']})
        with urllib.request.urlopen(request, timeout=2):
            return True
    except (OSError, ValueError, KeyError):
        return False


def stop(data):
    pattern = f'--data-dir {data}'
    subprocess.run(['pkill', '-f', '--', pattern])
    for _ in range(50):
        if subprocess.run(['pgrep', '-f', '--', pattern], stdout=subprocess.DEVNULL).returncode:
            return
        time.sleep(0.1)
    raise SystemExit(f'The scratch service is still running. Stop it with: pkill -f -- "{pattern}"')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    library, out = args.library.resolve(), args.out.resolve()
    if live(library):
        raise SystemExit(f'A service is running on {library}. Quit it before you copy the library.')
    steps = json.loads(args.steps.read_text())
    out.mkdir(parents=True, exist_ok=True)
    scratch, data = out / '.scratch', out / '.scratch/library'
    stop(data)
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir()
    # The app resolves snapshot names beside the step file.
    (out / 'steps.json').write_text(json.dumps(steps, indent=2))
    for step in steps:
        if 'snapshot' in step:
            (out / step['snapshot']).unlink(missing_ok=True)
    bundle = scratch / 'Applications/LocalXiv.app'
    executable = bundle / 'Contents/MacOS/PapersToKindle'
    subprocess.run(['xcrun', 'swiftc', '-D', 'LOCALXIV_AUTOMATION', '-module-cache-path', scratch / 'swift-cache',
                    '-target', f'{platform.machine()}-apple-macosx26.0', '-O',
                    *sorted((ROOT / 'app/macos').glob('*.swift')), '-o', scratch / 'PapersToKindle'], check=True)
    # The checkout's .venv from docs/development.md installs and runs the service: the newest Homebrew
    # python3 can lack wheels that load, and launch.command puts Homebrew first on PATH.
    python = ROOT / '.venv/bin/python3'
    if not python.exists():
        python = Path(sys.executable)
    subprocess.run([ROOT / 'install-app.sh'], check=True, stdout=subprocess.DEVNULL,
                   env={**os.environ, 'PATH': f'{python.parent}:{os.environ["PATH"]}',
                        'PAPERS_INSTALL_ROOT': str(scratch), 'PAPERS_APPLICATIONS_DIR': str(scratch / 'Applications')})
    launcher = scratch / 'app/launch.command'
    text = launcher.read_text().replace('port=8765', 'port=0', 1).replace('exec python3 ', f'exec "{python}" ', 1)
    if 'port=8765' in text or str(python) not in text:
        raise SystemExit(f'{launcher} changed; update the rewrite in {__file__}.')
    launcher.write_text(text)
    shutil.copy2(scratch / 'PapersToKindle', executable)
    info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
    # Its own bundle identifier keeps window frames and WebKit storage apart from the installed app.
    info['CFBundleIdentifier'] += '.automation'
    (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    subprocess.run(['codesign', '--force', '--sign', '-', bundle], check=True, stderr=subprocess.DEVNULL)
    subprocess.run(['cp', '-Rc', library, data], check=True)
    (data / 'session.json').unlink(missing_ok=True)
    seconds = 60 + sum(step.get('wait', 0) for step in steps)
    try:
        result = subprocess.run([executable], env={**os.environ, 'LOCALXIV_AUTOMATION': str(out / 'steps.json')},
                                timeout=seconds)
        failed = result.returncode != 0
    except subprocess.TimeoutExpired:
        print(f'The app did not quit within {seconds} seconds. See {data / "server.log"}.', file=sys.stderr)
        failed = True
    finally:
        stop(data)
    for step in steps:
        if 'snapshot' in step:
            path = out / step['snapshot']
            failed |= not path.is_file()
            print(path if path.is_file() else f'missing: {path}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
