"""Loopback HTTP application and one durable, cooperative job worker."""
import argparse
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import sys
import time
import shutil
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from papers.library import Library, TERMINAL
from papers.ai import Provider, answer_question, generate_overview, PROMPT_REVISION
from papers.settings import get_key, set_key
from papers.recommendations import CACHE_ID, DAY, POLICY, fingerprint, discover, recommend

DEFAULTS = {'endpoint': 'https://api.openai.com/v1', 'model': '', 'auto_send': False, 'auto_summary': True,
            'max_context_chars': 480000, 'max_output_tokens': 24576, 'timeout': 150}
STATIC = Path(__file__).parent / 'static'


class Cancelled(Exception):
    pass


class Application:
    def __init__(self, root, token=None):
        self.library = Library(Path(root))
        self.token = token or secrets.token_urlsafe(32)
        self.queue = queue.Queue()
        self.lock = threading.RLock()
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    def settings(self):
        return dict(DEFAULTS, **self.library.get_settings())

    def public_settings(self):
        result = self.settings()
        result['kindle_email'] = result.get('kindle_address', '')
        try:
            result['has_key'] = bool(get_key(result['endpoint']))
        except RuntimeError:
            result['has_key'] = False
        return result

    def submit(self, kind, payload):
        with self.lock:
            job = self.library.create_job(kind, payload)
            # Queueing the same reservation twice is harmless: worker checks state.
            self.queue.put(job['id'])
            return job

    def recommendations(self, papers, settings):
        if not papers or not settings.get('model') or not settings.get('has_key'):
            return {'items': []}
        with self.lock:
            cache = self.library.get_generation(CACHE_ID, 'recommendations') or {}
            stamp = fingerprint(papers, settings)
            active = any(j['kind'] == 'recommend' and j['state'] not in TERMINAL for j in self.library.list_jobs())
            if not active and (cache.get('fingerprint') != stamp or time.time() - cache.get('attempted_at', 0) >= DAY):
                # Reserve before queueing; failed/cancelled requests also wait until tomorrow.
                cache = dict(cache, fingerprint=stamp, attempted_at=time.time())
                self.library.save_generation(CACHE_ID, 'recommendations', cache)
                self.submit('recommend', {'fingerprint': stamp})
            saved = {re.sub(r'v\d+$', '', p['id']) for p in papers}
            return {'items': [item for item in cache.get('items', []) if cache.get('policy') == POLICY and re.sub(r'v\d+$', '', item['id']) not in saved],
                    'updated_at': cache.get('updated_at')}

    def cancel(self, job_id):
        with self.lock:
            job = self.library.get_job(job_id)
            if not job:
                raise KeyError(job_id)
            if job['state'] not in TERMINAL:
                job = self.library.update_job(job_id, state='cancelled', progress='Cancelled; any running operation will stop at its next safe checkpoint')
            return job

    def checkpoint(self, job_id, message=None):
        with self.lock:
            if self.library.get_job(job_id)['state'] == 'cancelled':
                raise Cancelled()
            if message:
                self.library.update_job(job_id, progress=message)

    def _work(self):
        while True:
            job_id = self.queue.get()
            try:
                if job_id is None:
                    return
                with self.lock:
                    job = self.library.get_job(job_id)
                    if job['state'] != 'queued':
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
                        try:
                            key = get_key(self.settings()['endpoint'])
                            if key:
                                message = message.replace(key, '[REDACTED]')
                        except RuntimeError:
                            pass
                        self.library.update_job(job_id, state='failed', error=message[:2000] or 'Operation failed.')
            finally:
                self.queue.task_done()

    def execute(self, job):
        progress = lambda text: self.checkpoint(job['id'], text)
        payload, kind = job['payload'], job['kind']
        if kind == 'recommend':
            papers, settings = self.library.list_papers(), self.settings()
            key = get_key(settings['endpoint']) if settings.get('model') else None
            if not papers or not key or fingerprint(papers, settings) != payload['fingerprint']:
                return {}
            progress('Finding related papers')
            candidates = discover(papers)
            progress('Choosing a few papers for your library')
            bounded = dict(settings, max_context_chars=min(settings.get('max_context_chars', 480000), 12000),
                           max_output_tokens=min(settings.get('max_output_tokens', 24576), 900),
                           timeout=min(settings.get('timeout', 150), 60))
            items = recommend(Provider(bounded, key, on_usage=lambda usage: self.library.record_usage('recommend',settings['model'],usage)), papers, candidates)
            with self.lock:
                self.checkpoint(job['id'])
                cache = self.library.get_generation(CACHE_ID, 'recommendations') or {}
                if fingerprint(self.library.list_papers(), self.settings()) == payload['fingerprint']:
                    self.library.save_generation(CACHE_ID, 'recommendations', dict(cache, items=items, policy=POLICY, updated_at=time.time()))
            return {}
        if kind == 'import':
            from papers.acquire import acquire
            from papers.convert import convert_paper
            directory = self.library.root / 'jobs' / job['id']
            directory.mkdir(parents=True, exist_ok=True)
            progress('Downloading the exact paper version')
            try:
                metadata = acquire(payload['url'], directory)
            except Exception as error:
                metadata_path = directory / 'metadata.json'
                if not metadata_path.is_file():
                    raise
                metadata = json.loads(metadata_path.read_text())
                document = self.pdf_fallback(job, directory, metadata, error, source_unavailable=True)
            else:
                progress('Converting paper source')
                try:
                    document = convert_paper(directory, metadata, progress)
                except Cancelled:
                    raise
                except Exception as error:
                    document = self.pdf_fallback(job, directory, metadata, error)
            paper_id = metadata['arxiv_id']
            destination = self.library.root / 'papers' / hashlib.sha256((paper_id + document['source_digest'] + json.dumps(document, sort_keys=True)).encode()).hexdigest()
            with self.lock:
                self.checkpoint(job['id'])
                existing = self.library.get_paper(paper_id)
                if document.get('format') == 'pdf' and existing and existing.get('status') not in ('conversion_failed', 'pdf_fallback'):
                    self.library.update_job(job['id'], result={'paper_id': paper_id})
                    raise ValueError('EPUB conversion failed on retry. Your previously converted paper is still available.')
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    shutil.rmtree(directory)
                else:
                    directory.rename(destination)
                self.library.save_paper(paper_id, document, str(destination))
                result = {'paper_id': paper_id, 'format': document.get('format', 'epub')}
                if result['format'] == 'pdf':
                    result['warning'] = document['report']['warning']
                self.library.update_job(job['id'], state='ready', progress='Imported PDF' if result['format'] == 'pdf' else 'Imported', result=result)
                settings = self.settings()
                if not payload.get('tutorial') and (document.get('format') != 'pdf' or document.get('passages')) and settings['auto_summary'] and settings.get('model'):
                    try:
                        key = get_key(settings['endpoint'])
                        if key:
                            Provider(settings, key)
                            self.submit('summary', {'paper_id': paper_id})
                    except RuntimeError:
                        pass  # Reading remains available when AI setup is incomplete.
                if not payload.get('tutorial') and settings['auto_send']:
                    self.submit('send', {'paper_id': paper_id, 'kind': 'paper'})
                self.recommendations(self.library.list_papers(), self.public_settings())
            return result
        paper = self.library.get_paper(payload['paper_id'])
        if not paper:
            raise ValueError('Paper no longer exists.')
        directory = Path(paper['directory'])
        if kind in ('summary', 'chat'):
            settings = self.settings()
            provider = Provider(settings, get_key(settings['endpoint']), on_usage=lambda usage: self.library.record_usage(kind,settings['model'],usage,paper['id']))
            if kind == 'summary':
                result = generate_overview(provider, paper, progress)
                result['model'] = settings['model']
                with self.lock:
                    self.checkpoint(job['id'])
                    self.library.save_generation(paper['id'], 'overview', result)
            else:
                question = payload['question']
                broad = re.search(
                    r'\b(?:overview|overall|whole paper|entire paper|all sections|main (?:findings|results|contributions)|key contributions)\b'
                    r'|\b(?:summarize|summarise|summarization|summary of)\s+(?:(?:this|the|entire|whole)\s+)*paper\b'
                    r'|^\s*(?:please\s+)?(?:explain|describe|outline)\s+(?:(?:this|the|paper[’\']s)\s+)*(?:method|approach|methodology)\s*[?.!]*\s*$',
                    question, re.I)
                # Question scaffolding should not retrieve every occurrence of 'the' or 'paper'.
                stopwords = {'a', 'an', 'the', 'this', 'that', 'paper', 'method', 'does', 'do', 'did', 'is', 'are', 'was', 'were', 'what', 'which', 'how', 'why', 'when', 'where', 'who', 'for', 'of', 'in', 'on', 'to', 'and', 'or', 'with', 'about', 'please', 'explain', 'describe', 'report', 'perform'}
                query = ' '.join(term for term in re.findall(r'\w+', question) if term.lower() not in stopwords)
                passages = self.library.passages(paper['id'], '' if broad else query) if broad or query else []
                if broad and sum(len(p['text']) + len(p.get('section', '')) + 20 for p in passages) > provider.context_limit - len(question) - 2000:
                    raise ValueError('This whole-paper question exceeds the configured context bound. Increase the context bound, or ask about a specific named result, figure, or section.')
                # Conversation is optional context; reserve space for the complete question and evidence.
                budget = max(0, provider.context_limit - len(question) - sum(len(p['text']) + len(p.get('section', '')) + 20 for p in passages) - 3000)
                history = self.library.messages(paper['id'])
                while history and len(json.dumps([{'role': m['role'], 'content': m['content']} for m in history], ensure_ascii=False)) > budget:
                    history = history[2:] if len(history) > 1 else []
                result = answer_question(provider, question, passages, history)
                with self.lock:
                    self.checkpoint(job['id'])
                    self.library.add_message(paper['id'], 'user', question, [])
                    self.library.add_message(paper['id'], 'assistant', result['text'], result['sources'], metadata={
                        'model': settings['model'], 'prompt_revision': PROMPT_REVISION,
                        'source_digest': paper.get('source_digest'), 'document_digest': paper.get('document_digest'),
                        'usage': result.get('usage', {}), 'evidence_passages': [p['id'] for p in passages],
                        'evidence_scope': 'full_paper' if broad else 'search_with_neighbors'})
            return {'paper_id': paper['id']}
        progress('Preparing file')
        artifact = self.artifact(paper, payload.get('kind', 'paper'), payload.get('profile', 'kindle'))
        file_format = artifact.suffix.removeprefix('.').upper()
        if kind == 'send':
            from native.host import send_with_mail, validate_kindle_email
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
                self.library.update_job(job['id'], state='ready', progress='Handed to Mail; Kindle delivery is unconfirmed', result=delivery)
            return delivery
        return {'download_url': '/files/' + urllib.parse.quote(paper['id'], safe='') + '/' + artifact.name}

    def pdf_fallback(self, job, directory, metadata, error, *, source_unavailable=False):
        from papers.convert import convert_paper
        from papers.pdf import PDF_NOTICE
        report_path = directory / 'conversion-report.json'
        report = json.loads(report_path.read_text()) if report_path.is_file() else {}
        report['epub_error'] = str(error)[:2000]
        report['warning'] = ('We downloaded the PDF instead of an EPUB because the paper’s source files were unavailable. '
                             'Sending this paper will send the PDF.') if source_unavailable else PDF_NOTICE
        report_path.write_text(json.dumps(report, indent=2))
        try:
            self.checkpoint(job['id'], 'EPUB unavailable. Opening the downloaded PDF.')
            return convert_paper(directory, metadata, lambda message: self.checkpoint(job['id'], message), pdf_only=True)
        except Cancelled:
            raise
        except Exception as pdf_error:
            message = f'{error}\nThe PDF fallback is also unavailable: {pdf_error}'
            self.preserve_failed_import(job, directory, metadata, message)
            raise ValueError(message) from pdf_error

    def preserve_failed_import(self, job, directory, metadata, error):
        with self.lock:
            self.checkpoint(job['id'])
            paper_id = metadata['arxiv_id']
            existing = self.library.get_paper(paper_id)
            if not existing or existing.get('status') == 'conversion_failed':
                pdf = directory / 'original.pdf'
                artifacts = {}
                if pdf.is_file():
                    with pdf.open('rb') as stream:
                        if stream.read(5) == b'%PDF-':
                            artifacts['original_pdf'] = 'original.pdf'
                report = {'error': str(error)[:2000], 'status': 'conversion_failed'}
                (directory / 'report.json').write_text(json.dumps(report, indent=2))
                document = dict(metadata, status='conversion_failed', chapters=[], passages=[], report=report, artifacts=artifacts)
                self.library.save_paper(paper_id, document, str(directory))
            self.library.update_job(job['id'], result={'paper_id': paper_id})

    def artifact(self, paper, kind, profile):
        directory = Path(paper['directory'])
        original = directory / ('semantic.epub' if profile == 'semantic' else 'paper.epub')
        if paper.get('format') == 'pdf':
            original = directory / 'original.pdf'
            if kind == 'both':
                raise ValueError('This paper is a PDF. Download or send the paper PDF and overview EPUB separately.')
        if kind == 'paper':
            artifact = original
        else:
            from papers.document import export_overview
            overview = self.library.get_generation(paper['id'], 'overview')
            if not overview:
                raise ValueError('Generate an overview before exporting or sending it.')
            artifact = export_overview(directory, paper, overview)
            if profile == 'semantic':
                artifact = directory / 'overview-semantic.epub'
                shutil.copyfile(directory / 'overview-export' / 'semantic.epub', artifact)
            if kind == 'both':
                from native.host import build_anthology, PaperMetadata
                overview_metadata = PaperMetadata(paper['title'] + ' — Overview', paper['authors'], paper['arxiv_id'])
                metadata = PaperMetadata(paper['title'], paper['authors'], paper['arxiv_id'])
                combined = directory / ('combined-semantic.epub' if profile == 'semantic' else 'combined.epub')
                candidate = directory / ('.' + combined.name)
                try:
                    build_anthology([(overview_metadata, artifact), (metadata, original)], paper['title'], candidate)
                    if not shutil.which('epubcheck'):
                        raise ValueError('Install EPUBCheck to validate the combined book.')
                    check = subprocess.run(['epubcheck', str(candidate)], capture_output=True, text=True, timeout=120)
                    combined.with_suffix('.epubcheck.log').write_text(check.stdout + check.stderr)
                    if check.returncode:
                        raise ValueError('Combined EPUB validation failed: ' + (check.stdout + check.stderr)[-1800:])
                    candidate.replace(combined)
                finally:
                    candidate.unlink(missing_ok=True)
                artifact = combined
        if not artifact.is_file():
            raise ValueError('The requested file is unavailable. Retry importing the paper.')
        return artifact

    def close(self):
        self.queue.put(None)


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
        policy = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; frame-ancestors 'self'; sandbox allow-same-origin" if paper else "default-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        if paper and content_type == 'application/pdf':
            # Browser PDF viewers cannot load inside a CSP-sandboxed document.
            # Keep the sandbox for converted HTML and restrict this to PDF bytes.
            policy = "default-src 'none'; frame-ancestors 'self'"
        self.send_header('Content-Security-Policy', policy)
        if cookie:
            self.send_header('Set-Cookie', 'papers_file=' + self.server.app.token + '; Path=/files/; HttpOnly; SameSite=Strict')
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
                papers, settings = app.library.list_papers(), app.public_settings()
                recommendations = app.recommendations(papers, settings)
                return self.respond(200, {'papers': papers, 'jobs': app.library.list_jobs(), 'settings': settings, 'recommendations': recommendations, 'dependencies': {name: bool(shutil.which(name)) for name in ('pandoc', 'latexml', 'latexmlpost', 'rsvg-convert', 'node', 'sandbox-exec', 'epubcheck', 'gs')}})
            if parts == ['api', 'health']:
                return self.respond(200, {'application': 'papers-to-kindle'})
            if len(parts) == 3 and parts[:2] == ['api', 'papers']:
                paper = app.library.get_paper(parts[2])
                if not paper:
                    raise KeyError(parts[2])
                return self.respond(200, {'paper': paper, 'overview': app.library.get_generation(parts[2], 'overview'), 'messages': app.library.messages(parts[2])})
            if parts[0] == 'files' and len(parts) >= 3:
                paper = app.library.get_paper(parts[1])
                if not paper:
                    raise KeyError(parts[1])
                base = Path(paper['directory']).resolve()
                relative = Path(*parts[2:])
                path = (base / relative).resolve()
                if any(p in ('..', '.', '') or '/' in p or '\\' in p for p in parts[2:]) or not path.is_relative_to(base):
                    return self.respond(403, {'error': 'Invalid file path.'})
                # Retained archives, job diagnostics, and metadata are not public downloads.
                if not (parts[2] == 'reader' or len(parts) == 3 and (path.suffix in ('.epub', '.pdf') or path.name in ('source', 'report.json'))):
                    return self.respond(403, {'error': 'File is not a reading artifact.'})
                return self.respond(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream', paper=True, cookie=True)
            if url.path == '/static/mathjax.js':
                path = STATIC.parent.parent / 'node_modules/mathjax-full/es5/tex-svg.js'
                return self.respond(200, path.read_bytes(), 'text/javascript')
            static = {'/static/math-config.js': 'math-config.js', '/': 'index.html', '/static/app.js': 'app.js', '/static/app.css': 'app.css'}.get(url.path)
            if static:
                path = STATIC / static
                return self.respond(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
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
        if parts == ['api', 'test-connection']:
            for field in ('endpoint', 'model', 'api_key'):
                if field in body and not isinstance(body[field], str):
                    raise ValueError('Connection fields must be text.')
            settings = dict(app.settings(), **{k:body[k].strip() for k in ('endpoint','model') if k in body},
                            timeout=20, max_context_chars=4000, max_output_tokens=512)
            key = body.get('api_key','').strip() or get_key(settings['endpoint'])
            if not key:
                raise ValueError('Enter an API key to test this connection.')
            provider = Provider(settings,key,on_usage=lambda usage: app.library.record_usage('connection',settings['model'],usage))
            gemini = urllib.parse.urlsplit(provider.url).hostname == 'generativelanguage.googleapis.com' and settings['model'].startswith('gemini-3')
            provider.complete([{'role':'user','content':'Reply with only OK.'}], **({'gemini_thinking_level':'low'} if gemini else {}))
            return self.respond(200, {'message':'Connection verified. The model responded successfully.'})
        if parts == ['api', 'settings']:
            values = {k: v for k, v in body.items() if k != 'api_key'}
            if 'kindle_email' in values:
                from native.host import validate_kindle_email
                values['kindle_address'] = validate_kindle_email(values.pop('kindle_email')) if values['kindle_email'] else ''
            for field in ('auto_send', 'auto_summary', 'onboarding_complete'):
                if field in values and not isinstance(values[field], bool):
                    raise ValueError('Automatic preferences must be true or false.')
            endpoint = values.get('endpoint', app.settings()['endpoint'])
            Provider({**app.settings(), **values, 'model': values.get('model') or 'validation'}, '')
            if body.get('api_key'):
                if not isinstance(body['api_key'], str):
                    raise ValueError('Invalid API key.')
                set_key(endpoint, body['api_key'])
            app.library.save_settings(values)
            return self.respond(200, app.public_settings())
        if parts == ['api', 'tutorial']:
            paper = app.library.get_paper('1706.03762v7')
            if paper and paper.get('chapters'):
                return self.respond(200, {'paper_id': paper['id']})
            return self.respond(202, {'job': app.submit('import', {'url': 'https://arxiv.org/abs/1706.03762v7', 'tutorial': True})})
        if parts == ['api', 'import']:
            from papers.acquire import paper_id
            paper_id(body.get('url', ''))
            return self.respond(202, {'job': app.submit('import', {'url': body['url']})})
        if len(parts) == 4 and parts[:2] == ['api', 'jobs'] and parts[3] == 'cancel':
            return self.respond(200, {'job': app.cancel(parts[2])})
        if len(parts) == 4 and parts[:2] == ['api', 'papers'] and parts[3] in ('summary', 'chat', 'export', 'send'):
            if not app.library.get_paper(parts[2]):
                raise KeyError(parts[2])
            payload = {'paper_id': parts[2]}
            if parts[3] == 'chat':
                if not isinstance(body.get('question'), str) or not body['question'].strip() or len(body['question']) > 12000:
                    raise ValueError('Enter a question of at most 12,000 characters.')
                payload['question'] = body['question'].strip()
            if parts[3] in ('export', 'send'):
                payload.update(kind=body.get('kind', 'paper'), profile=body.get('profile', 'kindle'))
                if payload['kind'] not in ('paper', 'overview', 'both') or payload['profile'] not in ('kindle', 'semantic'):
                    raise ValueError('Unknown artifact or reading profile.')
            return self.respond(202, {'job': app.submit(parts[3], payload)})
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
        request = urllib.request.Request(f"http://127.0.0.1:{saved['port']}/api/health", headers={'Authorization': 'Bearer ' + saved['token']})
        with urllib.request.urlopen(request, timeout=2) as response:
            if json.load(response).get('application') == 'papers-to-kindle':
                return saved
    except (OSError, ValueError, KeyError):
        pass
    return None


def queue_import(session, url):
    request = urllib.request.Request(f"http://127.0.0.1:{session['port']}/api/import", data=json.dumps({'url': url}).encode(), headers={'Authorization': 'Bearer ' + session['token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.load(response)
    if not result.get('job', {}).get('id'):
        raise ValueError('The local library did not confirm the import request.')
    return result['job']


def open_library(session, data_dir):
    bundle = Path.home() / 'Applications/LocalXiv.app'
    default = Path.home() / 'Library/Application Support/LocalXiv/library'
    if data_dir.resolve() == default.resolve() and (bundle / 'Contents/MacOS/PapersToKindle').is_file():
        subprocess.run(['/usr/bin/open', str(bundle)], check=True)
    else:
        webbrowser.open(f"http://127.0.0.1:{session['port']}/#token={session['token']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--import-url', help='Queue a paper URL in the local library and exit after acceptance')
    parser.add_argument('--data-dir', type=Path, default=Path.home() / 'Library/Application Support/LocalXiv/library')
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    session = args.data_dir / 'session.json'
    if args.import_url:
        from papers.acquire import paper_id
        paper_id(args.import_url)
    old = active_session(session)
    if args.import_url and not old:
        # The short-lived import command confirms queue acceptance, never conversion success.
        with (args.data_dir / 'server.log').open('ab') as log:
            subprocess.Popen([sys.executable, '-m', 'app.server', '--port', str(args.port), '--data-dir', str(args.data_dir)], cwd=str(Path(__file__).resolve().parent.parent), stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not old:
            time.sleep(0.2)
            old = active_session(session)
        if not old:
            raise SystemExit('The local library did not start. Open it and inspect server.log before retrying.')
    if old:
        if args.import_url:
            queue_import(old, args.import_url)
            print('Import queued. Follow progress in the local library.')
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
        server.app.close()
        session.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
