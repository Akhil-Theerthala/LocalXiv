"""Import recovery and isolated conversion without application credentials."""
from __future__ import annotations

import contextlib
import json
import hashlib
import os
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from papers.arxiv_html import retrieve
from papers.pdf import PDF_NOTICE


class Cancelled(Exception):
    """A cooperative checkpoint stopped the job; never try another conversion route."""


def convert_import(directory: Path, metadata: dict, progress, *, source_error=None, epub_only=False) -> dict:
    """Try Pandoc, arXiv HTML, LaTeXML, then PDF; retain diagnostics from each attempt."""

    report_path = directory / 'conversion-report.json'

    def record_failure(engine, error):
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        attempts = report.setdefault('attempts', [])
        # The worker reports detailed failures itself; retrieval and startup failures do not.
        if not attempts or attempts[-1].get('engine') != engine or attempts[-1].get('status') != 'failed':
            attempts.append({'engine': engine, 'status': 'failed', 'error': str(error)[:2000]})
        if engine == 'arxiv-html':
            report['html_recovery_error'] = str(error)[:2000]
        report_path.write_text(json.dumps(report, indent=2))

    error = source_error
    if source_error is None:
        progress('Converting paper source')
        try:
            return convert_paper(directory, metadata, progress, source_engine='pandoc')
        except Cancelled:
            raise
        except Exception as source_failure:
            error = source_failure
            record_failure('pandoc', error)
    try:
        retrieve(directory, metadata, progress)
        return convert_paper(directory, metadata, progress, html_only=True)
    except Cancelled:
        raise
    except Exception as html_error:
        record_failure('arxiv-html', html_error)
    if source_error is None:
        try:
            return convert_paper(directory, metadata, progress, source_engine='latexml')
        except Cancelled:
            raise
        except Exception as source_failure:
            error = source_failure
            record_failure('latexml', error)
    report = json.loads(report_path.read_text())
    report['epub_error'] = str(error)[:2000]
    report['warning'] = ('LocalXiv downloaded the PDF because the paper’s source files were unavailable. '
                         'Sending this paper sends the PDF.') if source_error is not None else PDF_NOTICE
    report_path.write_text(json.dumps(report, indent=2))
    if epub_only:
        raise ValueError(f'EPUB unavailable; original PDF retained. {error}')
    try:
        progress('EPUB unavailable. Opening the downloaded PDF.')
        return convert_paper(directory, metadata, progress, pdf_only=True)
    except Cancelled:
        raise
    except Exception as pdf_error:
        record_failure('pdf', pdf_error)
        raise ValueError(f'{error}\nThe PDF fallback is also unavailable: {pdf_error}') from pdf_error


def sandbox_profile(work: Path, app: Path, *readable: Path) -> str:
    reads = [app.resolve(), Path(sys.prefix).resolve(), Path(sys.executable).resolve().parent,
             Path(shutil.which('node') or '/usr/bin/node').resolve().parent, *(p.resolve() for p in readable)]
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
(deny file-write* (literal {json.dumps(str(work.resolve()))}))
'''


def special_files(directory: Path, *, remove=False) -> list[Path]:
    """Every entry under the directory that is not a regular file or a folder, such as a symbolic link."""
    def unreadable(error):
        raise ValueError(f'The conversion left a folder that LocalXiv cannot read: {error.filename}') from error
    found = []
    for parent, folders, files in os.walk(directory, onerror=unreadable):
        for name in folders + files:
            path = Path(parent, name)
            if not stat.S_ISDIR(mode := path.lstat().st_mode) and not stat.S_ISREG(mode):
                found.append(path)
                if remove:
                    path.unlink()
                if name in folders:  # A link to a folder; os.walk must not enter it.
                    folders.remove(name)
    return found


def _process_tree(root: int) -> dict[int, int]:
    """Resident kilobytes of each process in the root's group or below it by parent ID."""
    # ponytail: a child that calls setsid and forks again belongs to launchd, not to this tree.
    rows = [tuple(map(int, parts)) for row in subprocess.run(
        ['/bin/ps', '-axo', 'pid=,ppid=,pgid=,rss='], capture_output=True, text=True, timeout=5).stdout.splitlines()
        if len(parts := row.split()) == 4]
    tree = {pid for pid, _, group, _ in rows if root in (pid, group)}
    while added := {pid for pid, parent, _, _ in rows if parent in tree} - tree:
        tree |= added
    return {pid: rss for pid, _, _, rss in rows if pid in tree}


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000_000, 1_000_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))


def convert_paper(directory: Path, metadata: dict, progress=lambda _: None, *,
                   pdf_only=False, html_only=False, source_engine=None) -> dict:
    if source_engine not in (None, 'pandoc', 'latexml'):
        raise ValueError('Unknown source converter.')
    if sum((bool(pdf_only), bool(html_only), source_engine is not None)) > 1:
        raise ValueError('Choose one conversion format.')
    directory = directory.resolve()
    app = Path(__file__).resolve().parent.parent
    revision = hashlib.sha256()
    for name in ('native/host.py', 'papers/worker.py', 'papers/convert.py', 'papers/document.py',
                 'papers/citations.py', 'papers/pdf.py', 'papers/math.js', 'papers/math_fallback.py',
                 'papers/tex_math.js', 'papers/arxiv_html.py', 'papers/arxiv_html.js',
                 'papers/assets/ieee.csl', 'package-lock.json'):
        revision.update(name.encode())
        revision.update((app / name).read_bytes())
    metadata = {**metadata, 'conversion_revision': revision.hexdigest()}
    sandbox = shutil.which('sandbox-exec')
    if sys.platform != 'darwin' or not sandbox:
        raise ValueError('This build requires the macOS conversion sandbox.')
    (directory / 'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    # The worker reads the job folder and writes only work/. Every file the parent writes stays outside work/,
    # so a link that a paper source plants cannot redirect a write of the parent.
    work = directory / 'work'
    temp = work / 'temporary'
    temp.mkdir(parents=True, exist_ok=True)
    environment = {'PATH':os.environ.get('PATH','/usr/bin:/bin'), 'HOME':str(temp), 'TMPDIR':str(temp),
                   'LANG':'en_US.UTF-8', 'PYTHONPATH':str(app), 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONNOUSERSITE':'1',
                   'NODE_OPTIONS':'--max-old-space-size=1024', 'TEXMFOUTPUT':str(temp)}
    # The parser corpus test traces and skips TeX passes. The app sets neither variable.
    environment.update({name: os.environ[name] for name in ('LOCALXIV_PASS_TRACE', 'LOCALXIV_SKIP_PASS')
                        if os.environ.get(name)})
    runtime = app.parent / 'runtime'
    python = str(runtime / 'bin/python3') if runtime.is_dir() else sys.executable
    command = [sandbox, '-p', sandbox_profile(work, app, directory), python, '-m', 'papers.worker', str(directory)]
    if pdf_only:
        command.append('--pdf')
    if html_only:
        command.append('--html')
    if source_engine:
        command.append('--' + source_engine)
    process = subprocess.Popen(command,
                               cwd=work, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
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
            # macOS does not enforce RLIMIT_RSS. Check aggregate resident memory of the worker's processes.
            if time.monotonic() >= next_memory_check:
                next_memory_check = time.monotonic() + 5
                if sum(_process_tree(process.pid).values()) > 2_500_000:
                    raise ValueError('Conversion exceeded its memory limit. The source is retained.')
        if process.wait() != 0:
            raise ValueError('\n'.join(log[-12:]) or f'The conversion worker stopped with status {process.returncode}.')
    finally:
        selector.close()
        # The worker can exit before a converter descendant, and a descendant can leave the group with setsid.
        for pid in _process_tree(process.pid):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        process.stdout.close()
        (directory / ('pdf-worker.log' if pdf_only else 'worker.log')).write_text('\n'.join(log), encoding='utf-8')
        rejected = special_files(directory, remove=True)
        report = work / 'conversion-report.json'
        if report.is_file():
            report.replace(directory / 'conversion-report.json')
    if rejected:
        raise ValueError('The conversion made a link or a special file. LocalXiv removed it and rejected the '
                         'attempt: ' + ', '.join(str(path.relative_to(directory)) for path in rejected[:5]))
    for name in ('reader', 'paper.epub', 'semantic.epub', 'document.json'):
        output, previous = work / name, directory / name
        if output.exists():
            if previous.is_dir():
                shutil.rmtree(previous)
            output.replace(previous)
    return json.loads((directory / 'document.json').read_text())
