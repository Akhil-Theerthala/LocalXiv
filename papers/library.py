"""Local records and ordered full-text passages. Each operation owns its connection."""
from contextlib import contextmanager
import hashlib
import json
import re
import shutil
import sqlite3
import time
import uuid
import urllib.parse
from pathlib import Path

TERMINAL = ('ready', 'failed', 'interrupted', 'cancelled')
SETTING_KEYS = {'endpoint', 'model', 'provider', 'kindle_address', 'auto_send', 'auto_summary',
                'max_context_chars', 'max_output_tokens', 'timeout', 'onboarding_complete',
                'overview_language', 'overview_length', 'overview_vision'}


def document_digest(document):
    """Hash normalized content and anchors, excluding storage and run diagnostics."""
    content = {key: value for key, value in document.items()
               if key not in ('id', 'directory', 'document_digest', 'report')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


class Library:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'library.sqlite3'
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS usage (seq INTEGER PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS papers (id TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, reservation TEXT, value TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS active_reservation ON jobs(reservation) WHERE reservation IS NOT NULL;
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS generations (paper TEXT, kind TEXT, value TEXT, PRIMARY KEY(paper,kind));
                CREATE TABLE IF NOT EXISTS messages (seq INTEGER PRIMARY KEY, paper TEXT, value TEXT);
                CREATE VIRTUAL TABLE IF NOT EXISTS passage_search USING fts5(paper UNINDEXED, position UNINDEXED, value UNINDEXED, text);
            ''')
            # Older launchers moved the library without updating stored absolute paths.
            # Run inside the startup transaction so an interrupted repair retries safely.
            default = Path.home() / 'Library/Application Support/LocalXiv/library'
            if self.root.resolve() == default.resolve():
                old = default.parent.parent / 'PapersToKindle/library'
                for row in db.execute('SELECT id,value FROM papers').fetchall():
                    value = json.loads(row['value'])
                    directory = Path(value.get('directory', ''))
                    if not directory.is_absolute():
                        continue
                    try:
                        relative = directory.resolve().relative_to(old.resolve())
                    except ValueError:
                        continue
                    relocated = self.root.resolve() / relative
                    if not directory.exists() and relocated.is_dir():
                        value['directory'] = str(relocated)
                        db.execute('UPDATE papers SET value=? WHERE id=?', (json.dumps(value), row['id']))
            for row in db.execute('SELECT id,value FROM jobs').fetchall():
                value = json.loads(row['value'])
                if value['state'] not in TERMINAL:
                    value.update(state='interrupted', error='The application stopped before this operation finished. Retry explicitly.')
                    db.execute('UPDATE jobs SET reservation=NULL,value=? WHERE id=?', (json.dumps(value), row['id']))

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def seed_sample(self, source):
        """Install the offline example once, preserving edits and deliberate removal."""
        marker = self.root / '.attention-sample-installed'
        manifest = Path(source) / 'sample.json'
        if marker.exists() or not manifest.is_file():
            return
        sample = json.loads(manifest.read_text())
        paper = sample['paper']
        if not self.get_paper(paper['id']):
            directory = self.root / 'papers' / hashlib.sha256(paper['id'].encode()).hexdigest()
            shutil.copytree(source, directory, dirs_exist_ok=True)
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                value = dict(paper, directory=str(directory))
                db.execute('INSERT INTO papers VALUES (?,?)', (paper['id'], json.dumps(value)))
                db.executemany('INSERT INTO passage_search VALUES (?,?,?,?)',
                               [(paper['id'], i, json.dumps(p), p['text'])
                                for i, p in enumerate(paper.get('passages', []))])
                db.executemany('INSERT INTO generations VALUES (?,?,?)',
                               [(paper['id'], kind, json.dumps(generation))
                                for kind, generation in sample['generations'].items()])
        marker.touch()

    def list_papers(self, *, summaries=False):
        with self._connect() as db:
            projection = 'value'
            if summaries:
                fields = ('id', 'arxiv_id', 'title', 'authors', 'document_digest', 'format')
                arguments = ','.join(f"'{key}',json_extract(value,'$.{key}')" for key in fields)
                projection = f'json_object({arguments})'
            return [json.loads(row[0]) for row in db.execute(f'SELECT {projection} FROM papers ORDER BY rowid DESC')]

    def get_paper(self, paper_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_paper(self, paper_id, document, directory):
        value = dict(document, id=paper_id, directory=str(directory), document_digest=document_digest(document))
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
            if previous:
                previous = json.loads(previous[0])
                if document_digest(previous) != value['document_digest']:
                    db.execute('DELETE FROM generations WHERE paper=?', (paper_id,))
                    db.execute('DELETE FROM messages WHERE paper=?', (paper_id,))
            db.execute('INSERT OR REPLACE INTO papers VALUES (?,?)', (paper_id, json.dumps(value)))
            db.execute('DELETE FROM passage_search WHERE paper=?', (paper_id,))
            db.executemany('INSERT INTO passage_search VALUES (?,?,?,?)',
                           [(paper_id, i, json.dumps(p), p['text']) for i, p in enumerate(document.get('passages', []))])
        return value

    def remove_paper(self, paper_id):
        """Remove one owned paper directory and its searchable/personal records."""
        staged = None
        directory = None
        try:
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
                if not row:
                    raise KeyError(paper_id)
                directory = Path(json.loads(row[0])['directory'])
                owned = self.root.resolve() / 'papers'
                if directory.is_symlink() or directory.resolve().parent != owned:
                    raise ValueError('This paper is stored outside the library paper folder. No files were removed.')
                if directory.exists():
                    staged = self.root / ('.removed-' + uuid.uuid4().hex)
                    directory.rename(staged)
                for table in ('generations', 'messages', 'passage_search'):
                    db.execute(f'DELETE FROM {table} WHERE paper=?', (paper_id,))
                db.execute('DELETE FROM papers WHERE id=?', (paper_id,))
        except Exception:
            if staged is not None and staged.exists():
                staged.rename(directory)
            raise
        if staged is not None:
            try:
                shutil.rmtree(staged)
            except OSError as error:
                raise RuntimeError('Paper removed from the library, but some saved files could not be deleted.') from error

    def create_job(self, kind, payload):
        reservation = hashlib.sha256(json.dumps([kind, payload], sort_keys=True).encode()).hexdigest()
        value = dict(id=uuid.uuid4().hex, kind=kind, payload=payload, state='queued',
                     progress='Queued', result=None, error=None, created_at=time.time())
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT value FROM jobs WHERE reservation=?', (reservation,)).fetchone()
            if old:
                return json.loads(old[0])
            db.execute('INSERT INTO jobs VALUES (?,?,?)', (value['id'], reservation, json.dumps(value)))
        return value

    def update_job(self, job_id, **fields):
        if set(fields) - {'state', 'progress', 'result', 'error'}:
            raise ValueError('Unknown job field')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            value = json.loads(row[0])
            if value['state'] in TERMINAL and fields.get('state', value['state']) != value['state']:
                raise ValueError('Create a new job to retry a finished operation')
            value.update(fields)
            if value['state'] in TERMINAL:
                value.setdefault('finished_at', time.time())
            db.execute('UPDATE jobs SET value=? WHERE id=?', (json.dumps(value), job_id))
            if value['state'] in TERMINAL:
                db.execute('UPDATE jobs SET reservation=NULL WHERE id=?', (job_id,))
        return value

    def get_job(self, job_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM jobs WHERE id=?', (job_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def list_jobs(self, *, recent=None):
        with self._connect() as db:
            if recent is not None:
                return [json.loads(r[0]) for r in db.execute('''SELECT value FROM jobs
                    WHERE reservation IS NOT NULL OR rowid IN
                    (SELECT rowid FROM jobs WHERE reservation IS NULL
                     ORDER BY COALESCE(json_extract(value,'$.finished_at'),json_extract(value,'$.created_at')) DESC, rowid DESC LIMIT ?)
                    ORDER BY rowid DESC''', (recent,))]
            return [json.loads(r[0]) for r in db.execute('SELECT value FROM jobs ORDER BY rowid DESC')]

    def passages(self, paper_id, query=''):
        with self._connect() as db:
            rows = db.execute('SELECT position,value FROM passage_search WHERE paper=? ORDER BY CAST(position AS INTEGER)', (paper_id,)).fetchall()
            if not query.strip():
                return [json.loads(r['value']) for r in rows]
            terms = re.findall(r'\w+', query, re.UNICODE)
            if not terms:
                return []
            expression = ' OR '.join('"' + t + '"' for t in terms)
            hits = db.execute('SELECT position FROM passage_search WHERE paper=? AND passage_search MATCH ? ORDER BY rank LIMIT 12', (paper_id, expression)).fetchall()
            positions = {int(r[0]) + delta for r in hits for delta in (-1, 0, 1)}
            return [json.loads(r['value']) for r in rows if int(r['position']) in positions]

    def record_usage(self, kind, model, usage, paper_id=None):
        """Retain reported counts, never request content or provider credentials."""
        value = {'kind':kind, 'model':model, 'paper_id':paper_id, 'recorded_at':time.time(), **usage}
        with self._connect() as db:
            db.execute('INSERT INTO usage(value) VALUES (?)', (json.dumps(value),))

    def get_settings(self):
        with self._connect() as db:
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
            return json.loads(row[0]) if row else {}

    def save_settings(self, values):
        if 'endpoint' in values:
            endpoint = urllib.parse.urlsplit(values['endpoint'])
            if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise ValueError('Provider URL must not contain credentials, query, or fragment')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
            value = json.loads(row[0]) if row else {}
            value.update({k: v for k, v in values.items() if k in SETTING_KEYS})
            db.execute('INSERT OR REPLACE INTO settings VALUES (1,?)', (json.dumps(value),))
        return value

    def save_generation(self, paper_id, kind, value):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO generations VALUES (?,?,?)', (paper_id, kind, json.dumps(value)))
        return value

    def get_generation(self, paper_id, kind):
        with self._connect() as db:
            row = db.execute('SELECT value FROM generations WHERE paper=? AND kind=?', (paper_id, kind)).fetchone()
            return json.loads(row[0]) if row else None

    def add_message(self, paper_id, role, content, sources, metadata=None):
        if role not in ('user', 'assistant'):
            raise ValueError('Invalid message role')
        value = dict(role=role, content=content, sources=sources, created_at=time.time())
        if metadata is not None:
            value['metadata'] = dict(metadata)
        with self._connect() as db:
            db.execute('INSERT INTO messages(paper,value) VALUES (?,?)', (paper_id, json.dumps(value)))
        return value

    def messages(self, paper_id):
        with self._connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT value FROM messages WHERE paper=? ORDER BY seq', (paper_id,))]
