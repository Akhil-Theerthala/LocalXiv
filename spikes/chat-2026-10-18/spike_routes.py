"""P4 check 3: a throwaway streaming route on the app's own stdlib Handler.

GET /spike/stream?run=NAME&total=120&gap_at=25&gap=70 writes one line a second for `total` seconds, with no
write from `gap_at` to `gap_at + gap`. The Handler speaks HTTP/1.0, so the body ends when the connection closes,
as plan item C3 says. Each write and its result go to LOG as one JSON line, so a client disconnect shows as the
first write that raises.
"""
import json
import time
from urllib.parse import parse_qs, urlsplit

LOG = None


def _log(**fields):
    with open(LOG, 'a') as stream:
        stream.write(json.dumps({'at': round(time.time(), 3), **fields}) + '\n')


def _stream(handler):
    query = {key: values[0] for key, values in parse_qs(urlsplit(handler.path).query).items()}
    run, total = query.get('run', 'stream'), float(query.get('total', 120))
    gap_at, gap = float(query.get('gap_at', 25)), float(query.get('gap', 70))
    handler.send_response(200)
    handler.send_header('Content-Type', 'text/plain; charset=utf-8')
    handler.send_header('Cache-Control', 'no-store')
    handler.end_headers()
    start, line = time.monotonic(), 0
    _log(run=run, event='start', total=total, gap_at=gap_at, gap=gap, timeout=handler.connection.gettimeout())
    while (elapsed := time.monotonic() - start) < total:
        if gap_at <= elapsed < gap_at + gap:
            time.sleep(gap_at + gap - elapsed)
            continue
        try:
            handler.wfile.write(f'{line} {elapsed:.1f}\n'.encode())
            handler.wfile.flush()
        except OSError as error:
            _log(run=run, event='write-error', line=line, elapsed=round(elapsed, 2), error=type(error).__name__)
            return
        _log(run=run, event='write', line=line, elapsed=round(elapsed, 2))
        line += 1
        time.sleep(1)
    _log(run=run, event='done', lines=line, elapsed=round(time.monotonic() - start, 2))


def install(handler_class, log):
    global LOG
    LOG = log
    original = handler_class.handle_request

    def handle_request(self):
        if urlsplit(self.path).path == '/spike/stream':
            return _stream(self)
        return original(self)

    handler_class.handle_request = handle_request
    handler_class.do_GET = handler_class.do_POST = handle_request
