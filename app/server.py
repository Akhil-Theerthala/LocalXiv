"""Loopback HTTP application with durable jobs and one worker per paper."""
import argparse
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import shutil
import threading
import urllib.parse
import urllib.request
import webbrowser
from collections import deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from papers.library import Library, TERMINAL
from papers.convert import Cancelled, convert_import
from papers.exports import artifact as export_artifact
from native.host import send_with_mail, validate_kindle_email
from papers.acquire import ARXIV_ID, acquire, paper_id as parse_paper_id
from papers.ai import REASONING_EFFORTS, Provider, is_loopback, provider_limits
from papers.blog_workflow import generate as generate_blog
from papers.overview_workflow import generate as generate_figure_overview
from papers.search import S2, paper_search
from papers.settings import chat_account, delete_key, get_key, set_key
from papers.blog_prompts import overview_preferences

DEFAULTS = {'endpoint': 'https://api.openai.com/v1', 'model': '', 'auto_send': False, 'auto_summary': False,
            'overview_language': 'casual', 'overview_length': 'medium', 'overview_reasoning': 'auto',
            'open_imports': True, 'resume_reading': False, 'search_suggestions': True,
            'reading_theme': 'system', 'reading_font': 'new-york', 'reading_size': 18, 'reading_margins': 'normal',
            'reading_spacing': 'normal', 'chat_endpoint': '', 'chat_model': '', 'chat_reasoning': 'low',
            'chat_context': 200_000}
STATIC = Path(__file__).parent / 'static'
APP_ROOT = Path(__file__).resolve().parent.parent
BUNDLED = (APP_ROOT / 'release-id.txt').is_file() or (APP_ROOT.parent / 'runtime').is_dir()
# Read once: a running service must retain its identity after the app is replaced.
RUNTIME_ID = ((APP_ROOT / 'release-id.txt').read_text().strip()
              if (APP_ROOT / 'release-id.txt').is_file() else 'development') + '|' + str(APP_ROOT)
STALE_SERVICE = ('An older LocalXiv background service is still running. Wait for its jobs to finish, '
                 'then restart your Mac and open LocalXiv again. Your library is unchanged.')


class Application:
    def __init__(self, root, token=None):
        self.library = Library(Path(root))
        self.library.seed_sample(APP_ROOT / 'app/sample/attention')
        self.token = token or secrets.token_urlsafe(32)
        # The first job stays in its queue until execution stops, even after cancellation.
        self.queues = {}
        self.stopping_for_update = False
        self.lock = threading.RLock()

    def settings(self):
        return dict(DEFAULTS, **self.library.get_settings())

    def public_settings(self):
        result = self.settings()
        result['kindle_email'] = result.get('kindle_address', '')
        chat_endpoint = result['chat_endpoint']
        for field, account in (('has_key', result['endpoint']), ('has_s2_key', S2),
                               ('has_chat_key', chat_endpoint and chat_account(chat_endpoint))):
            try:
                result[field] = bool(account and get_key(account))
            except RuntimeError:
                result[field] = False
        result['chat_ready'] = bool(result['chat_model'] and (result['has_chat_key'] or is_loopback(chat_endpoint)))
        return result

    def submit(self, kind, payload):
        paper_id = payload.get('paper_id')
        if kind == 'import':
            paper_id = parse_paper_id(payload['url'])
        # An unversioned reimport can replace a saved version's files.
        paper_key = re.sub(r'v\d+$', '', paper_id) if paper_id else None
        with self.lock:
            if self.stopping_for_update:
                raise ValueError('LocalXiv is restarting to install an update. Try again after it opens.')
            job = self.library.create_job(kind, payload)
            if job['state'] != 'queued':
                return job
            if paper_key in self.queues:
                pending = self.queues[paper_key]
                if not any(item['id'] == job['id'] for item in pending):
                    pending.append(job)
            else:
                self.queues[paper_key] = deque([job])
                try:
                    threading.Thread(target=self._work, args=(paper_key,), daemon=True).start()
                except RuntimeError:
                    del self.queues[paper_key]
                    message = 'The task could not start. Try again.'
                    self.library.update_job(job['id'], state='failed', error=message)
                    raise ValueError(message) from None
            return job

    def prepare_update(self):
        """Reserve an idle service for shutdown without racing a newly submitted job."""
        with self.lock:
            if self.queues or self.library.list_jobs(recent=0):
                return False
            self.stopping_for_update = True
            return True

    def remove_paper(self, paper_id):
        with self.lock:
            jobs = self.library.list_jobs(recent=0)
            jobs.extend(pending[0] for pending in self.queues.values() if pending)
            if any(j['kind'] == 'import' or j['payload'].get('paper_id') == paper_id for j in jobs):
                raise ValueError('Wait for imports and work on this paper to finish, then remove it.')
            self.library.remove_paper(paper_id)

    def cancel(self, job_id):
        with self.lock:
            job = self.library.get_job(job_id)
            if not job:
                raise KeyError(job_id)
            if job['state'] not in TERMINAL:
                job = self.library.update_job(
                    job_id, state='cancelled',
                    progress='Cancelled; any running operation will stop at its next safe checkpoint')
            return job

    def checkpoint(self, job_id, message=None):
        with self.lock:
            if self.library.get_job(job_id)['state'] == 'cancelled':
                raise Cancelled()
            if message:
                self.library.update_job(job_id, progress=message)

    def _work(self, paper_key):
        while True:
            with self.lock:
                pending = self.queues[paper_key]
                if not pending:
                    del self.queues[paper_key]
                    return
                job = pending[0]
            job_id = job['id']
            try:
                with self.lock:
                    if self.library.get_job(job_id)['state'] != 'queued':
                        continue
                    self.library.update_job(job_id, state='running')
                result = self.execute(job)
                with self.lock:
                    self.checkpoint(job_id)
                    if self.library.get_job(job_id)['state'] not in TERMINAL:
                        self.library.update_job(job_id, state='ready', progress='Finished', result=result)
            except Cancelled:
                pass
            except Exception as error:
                with self.lock:
                    if self.library.get_job(job_id)['state'] not in TERMINAL:
                        # Provider exceptions already redact secrets. Never expose a traceback.
                        message = str(error)
                        settings = self.settings()
                        accounts = [settings['endpoint']]
                        if settings['chat_endpoint']:
                            accounts.append(chat_account(settings['chat_endpoint']))
                        for account in accounts:
                            try:
                                key = get_key(account)
                                if key:
                                    message = message.replace(key, '[REDACTED]')
                            except RuntimeError:
                                pass
                        self.library.update_job(job_id, state='failed', error=message[:2000] or 'Operation failed.')
            finally:
                with self.lock:
                    pending.popleft()

    def execute(self, job):
        def progress(text):
            self.checkpoint(job['id'], text)

        payload, kind = job['payload'], job['kind']
        if kind == 'import':
            directory = self.library.root / 'jobs' / job['id']
            directory.mkdir(parents=True, exist_ok=True)
            progress('Downloading the exact paper version')
            source_error = None
            try:
                metadata = acquire(payload['url'], directory)
            except Exception as error:
                metadata_path = directory / 'metadata.json'
                if not metadata_path.is_file():
                    raise
                metadata = json.loads(metadata_path.read_text())
                source_error = error
            try:
                document = convert_import(directory, metadata, progress, source_error=source_error)
            except Cancelled:
                raise
            except Exception as error:
                self.preserve_failed_import(job, directory, metadata, error)
                raise
            paper_id = metadata['arxiv_id']
            with self.lock:
                self.checkpoint(job['id'])
                self.library.update_job(job['id'], result={'paper_id': paper_id})
                self.library.retain_paper(document, directory)
                result = {'paper_id': paper_id, 'format': document.get('format', 'epub')}
                if result['format'] == 'pdf':
                    result['warning'] = document['report']['warning']
                self.library.update_job(job['id'], state='ready',
                                         progress='Imported PDF' if result['format'] == 'pdf' else 'Imported',
                                         result=result)
                settings = self.settings()
                if (document.get('passages') and settings.get('model') and
                        settings.get('auto_summary') and not payload.get('tutorial')):
                    try:
                        key = get_key(settings['endpoint'])
                        if key:
                            Provider(settings, key)
                            self.submit('overview', {'paper_id': paper_id})
                    except RuntimeError:
                        pass  # Manual Overview remains available when AI setup is incomplete.
                if not payload.get('tutorial') and settings['auto_send']:
                    self.submit('send', {'paper_id': paper_id, 'kind': 'paper'})
            return result
        paper = self.library.get_paper(payload['paper_id'])
        if not paper:
            raise ValueError('Paper no longer exists.')
        directory = Path(paper['directory'])
        if kind in ('blog', 'overview'):
            settings = self.settings()
            provider = Provider(
                settings, get_key(settings['endpoint']),
                on_usage=lambda usage: self.library.record_usage(kind,settings['model'],usage,paper['id']))
            if kind == 'overview':
                result = generate_figure_overview(provider, paper, progress)
            else:
                result = generate_blog(provider, paper, progress,
                                       image_overview=self.library.get_generation(paper['id'], 'overview'))
            result['model'] = settings['model']
            with self.lock:
                self.checkpoint(job['id'])
                self.library.save_generation(paper['id'], kind, result)
            return {'paper_id': paper['id']}
        progress('Preparing file')
        artifact = export_artifact(self.library, paper, payload.get('kind', 'paper'), payload.get('profile', 'kindle'))
        file_format = artifact.suffix.removeprefix('.').upper()
        if kind == 'send':
            recipient = validate_kindle_email(self.settings().get('kindle_address', ''))
            # Cancellation cannot race the irreversible Mail handoff.
            with self.lock:
                self.checkpoint(job['id'])
                delivery = {'paper_id': paper['id'], 'delivery': 'attempting_mail',
                            'recipient': recipient, 'artifact': artifact.name,
                            'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                            'kind': payload.get('kind', 'paper'), 'profile': payload.get('profile', 'kindle'),
                            'requested_at': job['created_at'], 'attempted_at': time.time()}
                self.library.update_job(job['id'], progress=f'Handing {file_format} to Mail', result=delivery)
                try:
                    send_with_mail(artifact, recipient, paper['title'])
                except Exception:
                    delivery['delivery'] = 'unknown'
                    self.library.update_job(job['id'], result=delivery)
                    raise
                delivery['delivery'] = 'handed_to_mail'
                self.library.update_job(job['id'], state='ready',
                                         progress='Handed to Mail; Kindle delivery is unconfirmed', result=delivery)
            return delivery
        return {'download_url': '/files/' + urllib.parse.quote(paper['id'], safe='') + '/' +
                urllib.parse.quote(str(artifact.resolve().relative_to(directory.resolve())), safe='/')}

    def preserve_failed_import(self, job, directory, metadata, error):
        with self.lock:
            self.checkpoint(job['id'])
            paper_id = metadata['arxiv_id']
            self.library.retain_paper(metadata, directory, error=error)
            self.library.update_job(job['id'], result={'paper_id': paper_id})


def request_key(body, field):
    """An API key from a request, trimmed. Blank means keep the saved key."""
    key = '' if body.get(field) is None else body[field]
    key = key.strip() if isinstance(key, str) else None
    # http.client cannot send other text as a header, and search.py would take that for an S2 outage.
    if key is None or not (key.isascii() and key.isprintable()):
        raise ValueError('Invalid API key.')
    return key


class Handler(BaseHTTPRequestHandler):
    server_version = 'PapersLocal/1'

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass  # URLs can contain session tokens.

    def respond(self, status, body, content_type='application/json', paper=False, cookie=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        policy = (
            "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; "
            # allow-scripts lets the app's own handlers run on paper elements in WebKit; default-src 'none'
            # still blocks every paper script.
            "frame-ancestors 'self'; sandbox allow-same-origin allow-scripts"
        ) if paper else (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        if paper and content_type == 'application/pdf':
            # Browser PDF viewers cannot load inside a CSP-sandboxed document.
            # Keep the sandbox for converted HTML and restrict this to PDF bytes.
            policy = "default-src 'none'; frame-ancestors 'self'"
        self.send_header('Content-Security-Policy', policy)
        if cookie:
            self.send_header('Set-Cookie',
                              'papers_file=' + self.server.app.token + '; Path=/files/; HttpOnly; SameSite=Strict')
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        app = self.server.app
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in allowed:
            return self.respond(403, {'error': 'Invalid Host.'})
        origin = self.headers.get('Origin')
        if origin and origin not in {'http://' + host for host in allowed}:
            return self.respond(403, {'error': 'Invalid Origin.'})
        url = urllib.parse.urlsplit(self.path)
        parts = [urllib.parse.unquote(part) for part in url.path.split('/')[1:]]
        protected = parts[0] in ('api', 'files')
        supplied = self.headers.get('Authorization', '').removeprefix('Bearer ')
        if parts[0] == 'files':
            supplied = urllib.parse.parse_qs(url.query).get('token', [supplied])[0]
            if not supplied:
                cookie = SimpleCookie(self.headers.get('Cookie', ''))
                supplied = cookie['papers_file'].value if 'papers_file' in cookie else ''
        if protected and not hmac.compare_digest(supplied, app.token):
            return self.respond(401, {'error': 'Open the app using its launcher to authenticate.'})
        if self.command == 'GET':
            if parts == ['api', 'state']:
                return self.respond(200, {
                    'papers': app.library.list_papers(summaries=True), 'jobs': app.library.list_jobs(recent=100),
                    'settings': app.public_settings(), 'provider_limits': provider_limits(),
                    'dependencies': {name: bool(shutil.which(name)) for name in (
                        'pandoc', 'latexml', 'latexmlpost', 'rsvg-convert', 'node', 'sandbox-exec',
                        'epubcheck', 'gs')}})
            if parts == ['api', 'health']:
                return self.respond(200, {'application': 'papers-to-kindle', 'runtime_id': RUNTIME_ID})
            if len(parts) == 3 and parts[:2] == ['api', 'papers']:
                paper = app.library.get_paper(parts[2])
                if not paper:
                    raise KeyError(parts[2])
                return self.respond(200, {'paper': paper, 'blog': app.library.get_generation(parts[2], 'blog'),
                                           'overview': app.library.get_generation(parts[2], 'overview'),
                                           'chat': app.library.list_chat_threads(parts[2])})
            if parts[0] == 'files' and len(parts) >= 3:
                paper = app.library.get_paper(parts[1])
                if not paper:
                    raise KeyError(parts[1])
                base = Path(paper['directory']).resolve()
                relative = Path(*parts[2:])
                path = (base / relative).resolve()
                if (any(p in ('..', '.', '') or '/' in p or '\\' in p for p in parts[2:])
                        or not path.is_relative_to(base)):
                    return self.respond(403, {'error': 'Invalid file path.'})
                # Retained archives, job diagnostics, and metadata are not public downloads.
                if not (parts[2] == 'reader' or len(parts) == 3
                        and (path.suffix in ('.epub', '.pdf') or path.name in ('source', 'report.json'))):
                    return self.respond(403, {'error': 'File is not a reading artifact.'})
                return self.respond(200, path.read_bytes(),
                                     mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
                                     paper=True, cookie=True)
            if url.path == '/static/mathjax.js':
                path = STATIC.parent.parent / 'node_modules/mathjax-full/es5/tex-svg.js'
                return self.respond(200, path.read_bytes(), 'text/javascript')
            name = 'index.html' if url.path == '/' else url.path.removeprefix('/static/')
            if (url.path == '/' or url.path.startswith('/static/') and '/' not in name
                    and name.endswith(('.js', '.css')) and (STATIC / name).is_file()):
                path = STATIC / name
                return self.respond(200, path.read_bytes(),
                                     mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            raise KeyError(url.path)
        if self.command != 'POST' or parts[0] != 'api':
            return self.respond(405, {'error': 'Method not allowed.'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('Use application/json.')
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 65536 or self.headers.get('Transfer-Encoding'):
            raise ValueError('Invalid request size.')
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError('Expected a JSON object.')
        if parts == ['api', 'update', 'shutdown']:
            if body.get('runtime_id') != RUNTIME_ID:
                return self.respond(409, {'error': 'The running app version changed. Reopen LocalXiv before updating.'})
            if not app.prepare_update():
                return self.respond(409, {'busy': True})
            self.respond(200, {'ready': True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if parts == ['api', 'test-connection']:
            for field in ('endpoint', 'model', 'api_key'):
                if field in body and not isinstance(body[field], str):
                    raise ValueError('Connection fields must be text.')
            role = body.get('role', 'overview')
            if role not in ('overview', 'chat'):
                raise ValueError('The role must be overview or chat.')
            settings = app.settings()
            if role == 'chat':
                settings.update(endpoint=settings['chat_endpoint'], model=settings['chat_model'])
            settings.update({k: body[k].strip() for k in ('endpoint', 'model') if k in body})
            key = body.get('api_key', '').strip() or get_key(
                chat_account(settings['endpoint']) if role == 'chat' else settings['endpoint'])
            if not key and not (role == 'chat' and is_loopback(settings['endpoint'])):
                raise ValueError('Enter an API key to test this connection.')
            provider = Provider(
                settings,key,on_usage=lambda usage: app.library.record_usage('connection',settings['model'],usage))
            provider.complete([{'role':'user','content':'Reply with only OK.'}])
            return self.respond(200, {'message':'Connection verified. The model responded successfully.'})
        if parts == ['api', 'settings']:
            values = {k: v for k, v in body.items() if k not in (
                'api_key', 's2_api_key', 'chat_api_key', 'chat_copy', 'chat_delete_key')}
            s2_key, chat_key = request_key(body, 's2_api_key'), request_key(body, 'chat_api_key')
            overview_preferences(values)
            if 'kindle_email' in values:
                values['kindle_address'] = (
                    validate_kindle_email(values.pop('kindle_email')) if values['kindle_email'] else '')
            for field in ('auto_send', 'auto_summary', 'onboarding_complete', 'open_imports', 'resume_reading',
                          'search_suggestions'):
                if field in values and not isinstance(values[field], bool):
                    raise ValueError('Automatic preferences must be true or false.')
            choices = {'reading_theme': ('system', 'light', 'sepia', 'dark'),
                       'reading_font': ('new-york', 'charter', 'iowan', 'palatino', 'sf-pro'),
                       'reading_margins': ('narrow', 'normal', 'wide'),
                       'reading_spacing': ('compact', 'normal', 'relaxed')}
            for field, options in choices.items():
                if field in values and values[field] not in options:
                    raise ValueError('Reading preference out of range.')
            size = values.get('reading_size', 18)
            if type(size) is not int or not 15 <= size <= 26:
                raise ValueError('Text size must be a whole number from 15 to 26.')
            if 'overview_reasoning' in values and values['overview_reasoning'] not in ('auto', *REASONING_EFFORTS):
                raise ValueError('Reasoning effort must be auto, low, medium, or high.')
            for field in ('chat_copy', 'chat_delete_key'):
                if field in body and not isinstance(body[field], bool):
                    raise ValueError('Chat actions must be true or false.')
            current = app.settings()
            endpoint = values.get('endpoint', current['endpoint'])
            if body.get('chat_copy'):
                values.update(chat_endpoint=endpoint, chat_model=values.get('model', current['model']))
            for field in ('chat_endpoint', 'chat_model'):
                if not isinstance(values.get(field, ''), str):
                    raise ValueError('Chat connection fields must be text.')
                if field in values:
                    values[field] = values[field].strip()
            if values.get('chat_reasoning', 'low') not in REASONING_EFFORTS:
                raise ValueError('Chat reasoning effort must be low, medium, or high.')
            context = values.get('chat_context', 200_000)
            if type(context) is not int or not 2048 <= context <= 2_000_000:
                raise ValueError('The Chat context size must be a whole number from 2,048 to 2,000,000.')
            chat_endpoint = values.get('chat_endpoint', current['chat_endpoint'])
            Provider({**current, **values, 'model': values.get('model') or 'validation'}, '')
            if chat_endpoint:
                Provider({'endpoint': chat_endpoint, 'model': 'validation'}, '')
            elif chat_key:
                raise ValueError('Choose a provider for the Chat model before you save its API key.')
            if body.get('api_key'):
                if not isinstance(body['api_key'], str):
                    raise ValueError('Invalid API key.')
                set_key(endpoint, body['api_key'])
            if s2_key:
                set_key(S2, s2_key)
            if body.get('chat_delete_key') and chat_endpoint:
                delete_key(chat_account(chat_endpoint))
            # A copy is a one-time action: the Chat key does not follow the Overview key afterward.
            if body.get('chat_copy') and (overview_key := get_key(endpoint)):
                set_key(chat_account(endpoint), overview_key)
            if chat_key:
                set_key(chat_account(chat_endpoint), chat_key)
            app.library.save_settings(values)
            return self.respond(200, app.public_settings())
        if parts == ['api', 'tutorial']:
            paper = app.library.get_paper('1706.03762v7')
            if paper and paper.get('chapters'):
                return self.respond(200, {'paper_id': paper['id']})
            return self.respond(202, {
                'job': app.submit('import', {'url': 'https://arxiv.org/abs/1706.03762v7', 'tutorial': True})})
        if parts == ['api', 'import']:
            identifier = parse_paper_id(body.get('url', ''))
            # A bare ID and its abstract link must reserve the same job.
            url = f'https://arxiv.org/abs/{identifier}' if ARXIV_ID.fullmatch(body['url'].strip()) else body['url']
            return self.respond(202, {'job': app.submit('import', {'url': url})})
        if parts == ['api', 'search']:
            query, limit = body.get('query'), body.get('limit')
            # A lone surrogate would fail later as a service failure and start the S2 cooldown.
            if (not isinstance(query, str) or not query.strip() or len(query.strip()) > 300
                    or re.search('[\ud800-\udfff]', query)):
                raise ValueError('Enter search text of at most 300 characters.')
            if type(limit) is not int or limit not in (8, 20):
                raise ValueError('The search limit must be 8 or 20.')
            return self.respond(200, paper_search(query.strip(), limit))
        if len(parts) == 4 and parts[:2] == ['api', 'jobs'] and parts[3] == 'cancel':
            return self.respond(200, {'job': app.cancel(parts[2])})
        if len(parts) == 4 and parts[:2] == ['api', 'papers'] and parts[3] == 'remove':
            app.remove_paper(parts[2])
            return self.respond(200, {'removed': parts[2]})
        if len(parts) == 4 and parts[:2] == ['api', 'papers'] and parts[3] == 'reading':
            if not app.library.get_paper(parts[2]):
                raise KeyError(parts[2])
            allowed = {'state': ('new', 'reading', 'read'), 'view': ('overview', 'blog', 'paper')}
            if set(body) - {'state', 'view', 'chapter', 'anchor', 'section'}:
                raise ValueError('Unknown reading field.')
            for key, value in body.items():
                if key in allowed and value not in allowed[key] or not isinstance(value, str) or len(value) > 300:
                    raise ValueError(f'Invalid {key}.')
            return self.respond(200, {'reading': app.library.save_reading(parts[2], body)})
        if (len(parts) == 4 and parts[:2] == ['api', 'papers']
                and parts[3] in ('blog', 'overview', 'export', 'send')):
            if not app.library.get_paper(parts[2]):
                raise KeyError(parts[2])
            payload = {'paper_id': parts[2]}
            ai = app.public_settings()
            if parts[3] in ('blog', 'overview') and not (ai['model'] and ai['has_key']):
                raise ValueError('Connect AI in Settings to generate an Overview or a Blog.')
            if parts[3] in ('export', 'send'):
                payload.update(kind=body.get('kind', 'paper'), profile=body.get('profile', 'kindle'))
                if (payload['kind'] not in ('paper', 'overview', 'blog', 'both')
                        or payload['profile'] not in ('kindle', 'semantic', 'pdf', 'png')):
                    raise ValueError('Unknown artifact or reading profile.')
                if payload['profile'] == 'png' and (parts[3] != 'export' or payload['kind'] != 'overview'):
                    raise ValueError('PNG export is only available for the Overview.')
            with app.lock:
                if not app.library.get_paper(parts[2]):
                    raise KeyError(parts[2])
                job = app.submit(parts[3], payload)
            return self.respond(202, {'job': job})
        raise KeyError(url.path)

    def handle_request(self):
        try:
            self.dispatch()
        except (KeyError, FileNotFoundError):
            self.respond(404, {'error': 'Not found.'})
        except (ValueError, TypeError, RuntimeError) as error:
            self.respond(400, {'error': str(error)[:1000]})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond(500, {'error': 'Request failed. Check application setup and retry.'})

    do_GET = handle_request
    do_POST = handle_request


def make_server(root, port=0, token=None):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.app = Application(root, token)
    return server


def active_session(session):
    try:
        saved = json.loads(session.read_text())
        request = urllib.request.Request(f"http://127.0.0.1:{saved['port']}/api/health",
                                          headers={'Authorization': 'Bearer ' + saved['token']})
        with urllib.request.urlopen(request, timeout=2) as response:
            health = json.load(response)
            if health.get('application') == 'papers-to-kindle':
                return {**saved, 'runtime_id': health.get('runtime_id')}
    except (OSError, ValueError, KeyError):
        pass
    return None


def open_library(session, data_dir):
    bundle = next((path for path in (Path('/Applications/LocalXiv.app'),
                                    Path.home() / 'Applications/LocalXiv.app')
                   if any((path / 'Contents/MacOS' / name).is_file()
                          for name in ('LocalXiv', 'PapersToKindle'))), None)
    default = Path.home() / 'Library/Application Support/LocalXiv/library'
    if data_dir.resolve() == default.resolve() and bundle is not None:
        subprocess.run(['/usr/bin/open', str(bundle)], check=True)
    else:
        webbrowser.open(f"http://127.0.0.1:{session['port']}/#token={session['token']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--data-dir', type=Path, default=Path.home() / 'Library/Application Support/LocalXiv/library')
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    session = args.data_dir / 'session.json'
    old = active_session(session)
    if old:
        if BUNDLED and old.get('runtime_id') != RUNTIME_ID:
            raise SystemExit(STALE_SERVICE)
        if args.open:
            open_library(old, args.data_dir)
        return
    # Serialize startup so Library recovery never interrupts another live instance.
    import fcntl
    lock_file = (args.data_dir / 'server.lock').open('a')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('The app is already starting. Launch again in a moment.')
    server = make_server(args.data_dir, args.port)
    fd = os.open(session, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'port': server.server_port, 'token': server.app.token}, stream)
    if args.open:
        open_library({'port': server.server_port, 'token': server.app.token}, args.data_dir)
    print(f'LocalXiv is running at http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
