"""Run source conversion without network access or application credentials."""
from __future__ import annotations

import json
import hashlib
import os
import resource
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def sandbox_profile(work: Path, app: Path) -> str:
    reads = [app.resolve(), Path(sys.prefix).resolve(), Path(sys.executable).resolve().parent,
             Path(shutil.which('node') or '/usr/bin/node').resolve().parent]
    runtime = app.resolve().parent / 'runtime'
    if runtime.is_dir():
        reads.append(runtime.resolve())
    literals = '\n'.join(f'(allow file-read* (subpath {json.dumps(str(p))}))' for p in reads)
    return f'''(version 1)
(deny default)
(allow process*)
(allow signal (target same-sandbox))
(allow sysctl-read)
(allow file-read-metadata)
(allow file-read* (literal "/"))
(allow file-read* (subpath "/System") (subpath "/usr") (subpath "/bin") (subpath "/sbin")
 (subpath "/opt/homebrew") (subpath "/Library/TeX") (subpath "/Library/Fonts") (subpath "/Library/Perl")
 (subpath "/private/etc") (subpath "/private/var/db/timezone") (subpath "/dev"))
(allow file-write* (literal "/dev/null") (literal "/dev/tty"))
(allow mach-lookup)
(deny mach-lookup (global-name "com.apple.securityd") (global-name "com.apple.coreservices.appleevents"))
(allow ipc-posix-shm)
{literals}
(allow file-read* file-write* (subpath {json.dumps(str(work.resolve()))}))
'''


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000_000, 1_000_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))


def convert_paper(directory: Path, metadata: dict, progress=lambda _: None, *, pdf_only=False, html_only=False, source_engine=None) -> dict:
    if source_engine not in (None, 'pandoc', 'latexml'):
        raise ValueError('Unknown source converter.')
    if sum((bool(pdf_only), bool(html_only), source_engine is not None)) > 1:
        raise ValueError('Choose one conversion format.')
    directory = directory.resolve()
    app = Path(__file__).resolve().parent.parent
    revision = hashlib.sha256()
    for name in ('native/host.py', 'papers/worker.py', 'papers/convert.py', 'papers/document.py',
                 'papers/citations.py', 'papers/pdf.py', 'papers/math.js', 'papers/math_fallback.py', 'papers/tex_math.js',
                 'papers/arxiv_html.py', 'papers/arxiv_html.js', 'papers/assets/ieee.csl', 'package-lock.json'):
        revision.update(name.encode())
        revision.update((app / name).read_bytes())
    metadata = {**metadata, 'conversion_revision': revision.hexdigest()}
    sandbox = shutil.which('sandbox-exec')
    if sys.platform != 'darwin' or not sandbox:
        raise ValueError('This build requires the macOS conversion sandbox.')
    (directory / 'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    profile = directory / 'worker.sb'
    profile.write_text(sandbox_profile(directory, app))
    temp = directory / 'temporary'
    temp.mkdir(exist_ok=True)
    environment = {'PATH':os.environ.get('PATH','/usr/bin:/bin'), 'HOME':str(temp), 'TMPDIR':str(temp),
                   'LANG':'en_US.UTF-8', 'PYTHONPATH':str(app), 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONNOUSERSITE':'1',
                   'NODE_OPTIONS':'--max-old-space-size=1024', 'TEXMFOUTPUT':str(temp)}
    runtime = app.parent / 'runtime'
    python = str(runtime / 'bin/python3') if runtime.is_dir() else sys.executable
    command = [sandbox, '-f', str(profile), python, '-m', 'papers.worker', str(directory)]
    if pdf_only:
        command.append('--pdf')
    if html_only:
        command.append('--html')
    if source_engine:
        command.append('--' + source_engine)
    process = subprocess.Popen(command,
                               cwd=directory, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True, preexec_fn=_limits)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    start = time.monotonic()
    next_memory_check = start
    pending = b''
    log = []
    try:
        while process.poll() is None or selector.get_map():
            if time.monotonic() - start > 660:
                raise ValueError('Conversion exceeded eleven minutes. The source and report are retained.')
            progress('Converting paper. This can take several minutes.')
            for key, _ in selector.select(timeout=1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                pending += chunk
                while b'\n' in pending:
                    line, pending = pending.split(b'\n',1)
                    text = line.decode('utf-8',errors='replace')
                    log.append(text)
                    if text.startswith('PROGRESS '):
                        progress(text[9:])
            # macOS does not enforce RLIMIT_RSS. Check aggregate resident memory of this process group.
            if time.monotonic() >= next_memory_check:
                next_memory_check = time.monotonic() + 5
                rows = subprocess.run(['/bin/ps','-axo','pgid=,rss='], capture_output=True, text=True, timeout=5).stdout.splitlines()
                rss = sum(int(parts[1]) for row in rows if len(parts:=row.split())==2 and parts[0]==str(process.pid))
                if rss > 2_500_000:
                    raise ValueError('Conversion exceeded its memory limit. The source is retained.')
        if process.wait() != 0:
            raise ValueError('\n'.join(log[-12:]) or f'The conversion worker stopped with status {process.returncode}.')
    finally:
        selector.close()
        # The worker can exit before a converter descendant. Clean its isolated group too.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        process.stdout.close()
        (directory / ('pdf-worker.log' if pdf_only else 'worker.log')).write_text('\n'.join(log), encoding='utf-8')
    return json.loads((directory / 'document.json').read_text())
