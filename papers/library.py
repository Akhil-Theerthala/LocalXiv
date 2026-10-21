"""Local records of papers, jobs, settings, and generations. Each operation owns its connection."""
from contextlib import closing, contextmanager
import hashlib
import json
import shutil
import sqlite3
import time
import uuid
import urllib.parse
from pathlib import Path

from papers.convert import special_files

TERMINAL = ('ready', 'failed', 'interrupted', 'cancelled')
SETTING_KEYS = {'endpoint', 'model', 'provider', 'kindle_address', 'auto_send', 'auto_summary',
                'onboarding_complete', 'open_imports', 'resume_reading', 'search_suggestions',
                'overview_language', 'overview_length', 'overview_reasoning', 'reading_theme', 'reading_font',
                'reading_size', 'reading_margins', 'reading_spacing',
                'chat_endpoint', 'chat_model', 'chat_reasoning', 'chat_context'}

# Records list in the order they were made, so a restored record returns to its place.
CREATED = "ORDER BY json_extract(value,'$.created_at'), rowid"
# A record gets these values for the fields it does not have, so a Release 1 record reads as a Question card.
RECORD_DEFAULTS = dict(colour='question', note='', head=None, prefix='', suffix='', section=None, end=None,
                       found='found', match=None, group=None, order=None)


def _record(value):
    return dict(RECORD_DEFAULTS, **json.loads(value))


def document_digest(document):
    """Hash normalized content and anchors, excluding storage and run diagnostics.

    The link form, the converter revision, and a PDF download error do not change the content, so
    a reimport that differs only in them keeps the saved Overview and Blog.
    """
    content = {key: value for key, value in document.items()
               if key not in ('id', 'directory', 'document_digest', 'report', 'original_url',
                              'conversion_revision', 'pdf_error')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


class Library:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'library.sqlite3'
        existed = self.path.exists()
        with self._connect() as db:
            # A new library has nothing to lose. A failed snapshot raises here, so the migration does not start.
            if existed and db.execute('PRAGMA user_version').fetchone()[0] < 1:
                self.backup(f'before-v1-{time.strftime("%Y-%m-%d")}')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS papers (id TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, reservation TEXT, value TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS active_reservation ON jobs(reservation) WHERE reservation IS NOT NULL;
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS generations (paper TEXT, kind TEXT, value TEXT, PRIMARY KEY(paper,kind));
                CREATE TABLE IF NOT EXISTS reading (paper TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS highlights (id TEXT PRIMARY KEY, paper TEXT NOT NULL, value TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS highlight_paper ON highlights(paper);
                CREATE TABLE IF NOT EXISTS note_groups (paper TEXT PRIMARY KEY, value TEXT NOT NULL);
                DROP TABLE IF EXISTS messages;
                DROP TABLE IF EXISTS passage_search;
                DROP TABLE IF EXISTS usage;
            ''')
            # Release 1 kept Question cards in chat_threads. They move once, in one transaction. IMMEDIATE makes a
            # second Library that starts at the same time wait, and then it finds no chat_threads.
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_threads'").fetchone():
                db.execute('INSERT OR IGNORE INTO highlights SELECT id, paper, value FROM chat_threads')
                db.execute('DROP TABLE chat_threads')
            # Generation kinds were renamed on 2026-09-18: the Blog was stored as 'overview' and
            # the Overview as 'bento'. user_version marks the library as renamed, so the rename
            # runs once and never touches rows the renamed kinds now own.
            if db.execute('PRAGMA user_version').fetchone()[0] < 1:
                db.execute("UPDATE generations SET kind='blog' WHERE kind='overview'")
                db.execute("UPDATE generations SET kind='overview' WHERE kind='bento'")
                db.execute('PRAGMA user_version = 1')
            for row in db.execute('SELECT id,value FROM jobs').fetchall():
                value = json.loads(row['value'])
                if value['state'] not in TERMINAL:
                    value.update(state='interrupted',
                                 error='The application stopped before this operation finished. Retry explicitly.')
                    db.execute('UPDATE jobs SET reservation=NULL,value=? WHERE id=?', (json.dumps(value), row['id']))
        self.daily_backup()

    def backup(self, name):
        """Copy the database to backups/<name>.sqlite3 with the SQLite backup API and return the path."""
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        # The copy gets its name only when it is whole, so a stop in the middle leaves no partial snapshot.
        partial = folder / f'{name}.{uuid.uuid4().hex}.tmp'
        try:
            with self._connect() as source, closing(sqlite3.connect(partial)) as target:
                source.backup(target)
            return partial.replace(folder / f'{name}.sqlite3')
        finally:
            partial.unlink(missing_ok=True)

    def daily_backup(self):
        """Write today's snapshot when it does not exist and keep the 7 newest. A full disk does not stop the app."""
        name = f'daily-{time.strftime("%Y-%m-%d")}'
        try:
            if not (self.root / 'backups' / f'{name}.sqlite3').exists():
                self.backup(name)
                # Date names sort in time order. Snapshots from before a migration are never deleted.
                for old in sorted((self.root / 'backups').glob('daily-*.sqlite3'))[:-7]:
                    old.unlink()
        except (OSError, sqlite3.Error):
            pass

    def backup_before_restore(self):
        """Write a snapshot before a restore of Notes and keep the 7 newest. A failure raises, so that no restore
        runs without its snapshot."""
        try:
            self.backup(f'before-restore-{time.strftime("%Y-%m-%d-%H%M%S")}')
            for old in sorted((self.root / 'backups').glob('before-restore-*.sqlite3'))[:-7]:
                old.unlink()
        except (OSError, sqlite3.Error):
            raise RuntimeError('LocalXiv restored nothing. It could not make a copy of the library first.') from None

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
                # A Paper records no date of its own; its first finished import is when it was added.
                projection = (f"json_object({arguments},"
                              "'overview',EXISTS(SELECT 1 FROM generations WHERE paper=papers.id AND kind='overview'),"
                              "'blog',EXISTS(SELECT 1 FROM generations WHERE paper=papers.id AND kind='blog'),"
                              "'reading',(SELECT json(value) FROM reading WHERE paper=papers.id),"
                              "'added_at',(SELECT MIN(json_extract(value,'$.finished_at')) FROM jobs "
                              "WHERE json_extract(value,'$.kind')='import' AND json_extract(value,'$.state')='ready' "
                              "AND json_extract(value,'$.result.paper_id')=papers.id))")
            return [json.loads(row[0]) for row in db.execute(f'SELECT {projection} FROM papers ORDER BY rowid DESC')]

    def get_paper(self, paper_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def get_reading(self, paper_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM reading WHERE paper=?', (paper_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_reading(self, paper_id, values):
        """Merge a validated partial record; state 'new' deletes it, so no record means New."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if values.get('state') == 'new':
                db.execute('DELETE FROM reading WHERE paper=?', (paper_id,))
                return None
            row = db.execute('SELECT value FROM reading WHERE paper=?', (paper_id,)).fetchone()
            record = json.loads(row[0]) if row else {'state': 'reading'}
            record.update(values, opened_at=time.time())
            if values.get('state') == 'read':
                record['read_at'] = time.time()
            elif values.get('state') == 'reading':
                record.pop('read_at', None)
            db.execute('INSERT OR REPLACE INTO reading VALUES (?,?)', (paper_id, json.dumps(record)))
            return record

    def save_highlight(self, record):
        """Write one Highlight, Note, Paper note, or Question card, replacing the record with the same id."""
        record = dict(RECORD_DEFAULTS, **record)
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO highlights VALUES (?,?,?)',
                       (record['id'], record['paper'], json.dumps(record)))
        return record

    def get_highlight(self, paper_id, highlight_id):
        """One record of the Paper, or of any Paper when paper_id is None."""
        with self._connect() as db:
            row = db.execute('SELECT paper,value FROM highlights WHERE id=?', (highlight_id,)).fetchone()
            return _record(row['value']) if row and paper_id in (None, row['paper']) else None

    def list_highlights(self, paper_id):
        with self._connect() as db:
            return [_record(row[0]) for row in db.execute(
                f'SELECT value FROM highlights WHERE paper=? {CREATED}', (paper_id,))]

    def delete_highlights(self, paper_id, ids):
        """Delete the listed records of a Paper and return what was removed."""
        where = f'paper=? AND id IN ({",".join("?" * len(ids))})'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute(f'SELECT value FROM highlights WHERE {where} {CREATED}', (paper_id, *ids)).fetchall()
            db.execute(f'DELETE FROM highlights WHERE {where}', (paper_id, *ids))
            return [_record(row[0]) for row in rows]

    def clear_chat(self, paper_id):
        """In one transaction, delete each open Question card (``kept`` false) and empty the turns of each other
        record that has turns. Returns each deleted or changed record as it was."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            records = [_record(row[0]) for row in db.execute(
                f'SELECT value FROM highlights WHERE paper=? {CREATED}', (paper_id,))]
            removed = [record for record in records if not record['kept'] or record['turns']]
            db.executemany('DELETE FROM highlights WHERE id=?',
                           [(record['id'],) for record in removed if not record['kept']])
            db.executemany('UPDATE highlights SET value=? WHERE id=?',
                           [(json.dumps(dict(record, turns=[])), record['id']) for record in removed if record['kept']])
            return removed

    def count_highlights(self, paper_id):
        with self._connect() as db:
            return db.execute('SELECT COUNT(*) FROM highlights WHERE paper=?', (paper_id,)).fetchone()[0]

    def copy_highlights(self, source, target):
        """In one transaction, write each record of `source` as a new record of `target`, with every other field as
        it is, and give `target` the Note groups of `source`. Returns the count."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            records = [dict(_record(row[0]), id=uuid.uuid4().hex, paper=target) for row in db.execute(
                f'SELECT value FROM highlights WHERE paper=? {CREATED}', (source,))]
            db.executemany('INSERT INTO highlights VALUES (?,?,?)',
                           [(record['id'], target, json.dumps(record)) for record in records])
            groups = db.execute('SELECT value FROM note_groups WHERE paper=?', (source,)).fetchone()
            db.execute('DELETE FROM note_groups WHERE paper=?', (target,))
            if groups:
                db.execute('INSERT INTO note_groups VALUES (?,?)', (target, groups[0]))
            return len(records)

    def get_groups(self, paper_id):
        with self._connect() as db:
            row = db.execute('SELECT value FROM note_groups WHERE paper=?', (paper_id,)).fetchone()
            return json.loads(row[0]) if row else []

    def save_groups(self, paper_id, groups):
        """Replace the ordered Note groups of a Paper."""
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO note_groups VALUES (?,?)', (paper_id, json.dumps(groups)))
        return groups

    def count_notes(self):
        """The number of records of the Papers in the library."""
        with self._connect() as db:
            return db.execute('SELECT COUNT(*) FROM highlights WHERE paper IN (SELECT id FROM papers)').fetchone()[0]

    def notes(self):
        """Every highlights row and the Note groups of each Paper, also of Papers that are not in the library."""
        with self._connect() as db:
            return ([_record(row[0]) for row in db.execute(f'SELECT value FROM highlights {CREATED}')],
                    {row[0]: json.loads(row[1]) for row in db.execute('SELECT paper,value FROM note_groups')})

    def import_notes(self, records, groups):
        """In one transaction, write each record over the record with its ID, and replace the Note groups of each
        Paper in `groups`."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.executemany('INSERT OR REPLACE INTO highlights VALUES (?,?,?)',
                           [(record['id'], record['paper'], json.dumps(record)) for record in records])
            db.executemany('INSERT OR REPLACE INTO note_groups VALUES (?,?)',
                           [(paper, json.dumps(value)) for paper, value in groups.items()])

    def retain_paper(self, document, directory, *, error=None):
        """Promote an import's files and records together; a failed retry keeps a ready Paper."""
        directory = Path(directory)
        if directory.is_symlink() or directory.resolve().parent != self.root.resolve() / 'jobs':
            raise ValueError('Only an owned import directory can be retained.')
        if special_files(directory):
            raise ValueError('The import directory contains a link or a special file, so LocalXiv did not keep it.')
        paper_id = document['arxiv_id']
        previous = self.get_paper(paper_id)
        if error is not None:
            if previous and previous.get('status') != 'conversion_failed':
                return previous
            pdf = directory / 'original.pdf'
            artifacts = {}
            if pdf.is_file():
                with pdf.open('rb') as stream:
                    if stream.read(5) == b'%PDF-':
                        artifacts['original_pdf'] = 'original.pdf'
            report = {'error': str(error)[:2000], 'status': 'conversion_failed'}
            (directory / 'report.json').write_text(json.dumps(report, indent=2))
            document = dict(document, status='conversion_failed', chapters=[], passages=[],
                            report=report, artifacts=artifacts)
        elif (document.get('format') == 'pdf' and previous
              and previous.get('status') not in ('conversion_failed', 'pdf_fallback')):
            raise ValueError('EPUB conversion failed on retry. Your previously converted paper is still available.')
        destination = self.root / 'papers' / directory.name
        backup = None
        if error is None and previous and document_digest(previous) == document_digest(document):
            retained = Path(previous['directory'])
            if (retained.is_dir() and not retained.is_symlink()
                    and retained.resolve().parent == self.root.resolve() / 'papers'):
                # Keep saved explanations, but let fresh import files repair missing or damaged originals.
                def copy_missing(source, target):
                    target = Path(target)
                    if not target.resolve().is_relative_to(directory.resolve()):
                        raise ValueError('A retained file points outside the import directory.')
                    if not target.exists():
                        shutil.copy2(source, target)
                shutil.copytree(retained, directory, dirs_exist_ok=True, copy_function=copy_missing,
                                ignore=lambda source, names: [name for name in names
                                                               if (Path(source) / name).is_symlink()])
                destination = retained
                backup = self.root / ('.replaced-' + uuid.uuid4().hex)
        # Each import owns its retained files, including useful diagnostics after failure.
        destination.parent.mkdir(parents=True, exist_ok=True)
        if backup is not None:
            destination.rename(backup)
        elif destination.exists() or destination.is_symlink():
            raise ValueError('This import already has retained files.')
        try:
            directory.rename(destination)
            saved = self.save_paper(paper_id, document, destination)
        except Exception:
            if not directory.exists():
                destination.rename(directory)
            if backup is not None:
                backup.rename(destination)
            raise
        if backup is not None:
            shutil.rmtree(backup)
        return saved

    def save_paper(self, paper_id, document, directory):
        value = dict(document, id=paper_id, directory=str(directory), document_digest=document_digest(document))
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
            if previous:
                previous = json.loads(previous[0])
                if document_digest(previous) != value['document_digest']:
                    db.execute('DELETE FROM generations WHERE paper=?', (paper_id,))
            db.execute('INSERT OR REPLACE INTO papers VALUES (?,?)', (paper_id, json.dumps(value)))
        return value

    def remove_paper(self, paper_id):
        """Remove one owned paper directory and its records."""
        staged = None
        directory = None
        try:
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()
                if not row:
                    raise KeyError(paper_id)
                paper = json.loads(row[0])
                directory = Path(paper['directory'])
                owned = self.root.resolve() / 'papers'
                legacy = False
                if (paper.get('status') == 'conversion_failed'
                        and directory.resolve().parent == self.root.resolve() / 'jobs'):
                    # Earlier builds retained failed Papers in their import job directory.
                    job = db.execute('SELECT value FROM jobs WHERE id=?', (directory.name,)).fetchone()
                    job = json.loads(job[0]) if job else {}
                    legacy = (job.get('kind') == 'import' and job.get('state') in TERMINAL
                              and (job.get('result') or {}).get('paper_id') == paper_id)
                if directory.is_symlink() or (directory.resolve().parent != owned and not legacy):
                    raise ValueError('This paper is stored outside the library paper folder. No files were removed.')
                if directory.exists():
                    staged = self.root / ('.removed-' + uuid.uuid4().hex)
                    directory.rename(staged)
                db.execute('DELETE FROM generations WHERE paper=?', (paper_id,))
                db.execute('DELETE FROM reading WHERE paper=?', (paper_id,))
                db.execute('DELETE FROM highlights WHERE paper=?', (paper_id,))
                db.execute('DELETE FROM note_groups WHERE paper=?', (paper_id,))
                db.execute('DELETE FROM papers WHERE id=?', (paper_id,))
        except Exception:
            if staged is not None and staged.exists():
                staged.rename(directory)
            raise
        if staged is not None:
            try:
                shutil.rmtree(staged)
            except OSError as error:
                raise RuntimeError(
                    'Paper removed from the library, but some saved files could not be deleted.') from error

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
                     ORDER BY COALESCE(json_extract(value,'$.finished_at'),'''
                    '''json_extract(value,'$.created_at')) DESC, rowid DESC LIMIT ?)
                    ORDER BY rowid DESC''', (recent,))]
            return [json.loads(r[0]) for r in db.execute('SELECT value FROM jobs ORDER BY rowid DESC')]

    def get_settings(self):
        with self._connect() as db:
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
            return {k: v for k, v in json.loads(row[0]).items() if k in SETTING_KEYS} if row else {}

    def save_settings(self, values):
        if 'endpoint' in values:
            endpoint = urllib.parse.urlsplit(values['endpoint'])
            if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise ValueError('Provider URL must not contain credentials, query, or fragment')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
            value = {k: v for k, v in json.loads(row[0]).items() if k in SETTING_KEYS} if row else {}
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
