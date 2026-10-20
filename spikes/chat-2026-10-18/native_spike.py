"""tools/native_shot.py with the P4 spike route added to its scratch copy of the server.

  python3 spikes/chat-2026-10-18/native_spike.py --log FILE --library DIR --steps STEPS.json --out DIR

native_shot installs the app into --out/.scratch. This script edits only that scratch copy, after install-app.sh,
so the WKWebView talks to the real stdlib Handler with the /spike/stream route of spike_routes.py.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
import native_shot  # noqa: E402

log = sys.argv[sys.argv.index('--log') + 1]
del sys.argv[sys.argv.index('--log'):sys.argv.index('--log') + 2]
real_run = subprocess.run


def run(args, *rest, **options):
    result = real_run(args, *rest, **options)
    if str(args[0]).endswith('install-app.sh'):
        server = Path(options['env']['PAPERS_INSTALL_ROOT']) / 'app/app/server.py'
        marker = "\nif __name__ == '__main__':"
        text = server.read_text()
        assert marker in text, server
        hook = (f"\nimport sys as _sys; _sys.path.insert(0, {str(HERE)!r})\n"
                f"import spike_routes; spike_routes.install(Handler, {log!r})\n")
        server.write_text(text.replace(marker, hook + marker, 1))
    return result


subprocess.run = run  # shortcut: patches the module for this throwaway process only
native_shot.main()
