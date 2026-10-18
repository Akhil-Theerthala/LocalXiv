"""Copy a few Papers from the user's library into a scratch library for the P4 WebKit checks.

  python spikes/chat-2026-10-18/make_library.py OUT_DIR [PAPER_ID ...]

The user's library is opened read only. The Paper folders are APFS clones (cp -c), so they cost no disk.
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from papers.library import Library  # noqa: E402

SOURCE = Path.home() / 'Library/Application Support/LocalXiv/library'
# Pandoc with MathML, arXiv HTML with MathML, and a PDF Paper.
DEFAULT = ['1706.03762v7', '2610.02887v1', '2609.37725v1']

out = Path(sys.argv[1]).resolve()
ids = sys.argv[2:] or DEFAULT
library = Library(out)
(out / 'papers').mkdir(exist_ok=True)
source = sqlite3.connect(f'file:{SOURCE / "library.sqlite3"}?mode=ro', uri=True)
with sqlite3.connect(library.path) as db:
    for paper_id in ids:
        value = json.loads(source.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()[0])
        target = out / 'papers' / Path(value['directory']).name
        if not target.exists():
            subprocess.run(['cp', '-Rc', value['directory'], target], check=True)
        value['directory'] = str(target)
        db.execute('INSERT OR REPLACE INTO papers VALUES (?,?)', (paper_id, json.dumps(value)))
# The scratch library never gets the bundled sample, so it holds only the Papers above.
(out / '.attention-sample-installed').touch()
os.chmod(library.path, 0o600)
print(out, ids)
