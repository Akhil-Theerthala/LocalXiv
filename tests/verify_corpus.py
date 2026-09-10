"""Run real source conversion against the recorded, versioned paper corpus."""
import argparse
import fcntl
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from papers.convert import convert_paper


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', nargs='*')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--force', action='store_true', help='Reconvert selected papers even if a previous build passed')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    corpus = json.loads((root / 'docs/verification/corpus.json').read_text())['papers']
    selected = set(args.ids or (paper['id'] for paper in corpus))
    unknown = selected - {paper['id'] for paper in corpus}
    if unknown:
        parser.error('Unknown corpus identifiers: ' + ', '.join(sorted(unknown)))
    output = root / 'docs/verification/conversion-results.json'
    results = json.loads(output.read_text()) if output.exists() else {}
    for paper in corpus:
        identifier = paper['id']
        if args.ids and identifier not in args.ids: continue
        if not args.force and identifier in results and not (args.retry_failed and results[identifier]['status'] != 'passed'): continue
        work = root / '.verification/converted' / identifier.replace('/','_')
        work.mkdir(parents=True,exist_ok=True)
        source = root / paper['directory']
        shutil.copyfile(source / 'source.tar', work / 'source')
        shutil.copyfile(source / 'paper.pdf', work / 'original.pdf')
        start = time.monotonic()
        record = {'id':identifier, 'title':paper['title'], 'source_sha256':paper['source_sha256'], 'directory':str(work.relative_to(root)), 'started_at': datetime.now(timezone.utc).isoformat()}
        print('START',identifier,paper['title'],flush=True)
        try:
            document = convert_paper(work, {'arxiv_id':identifier,'title':paper['title'],'authors':paper.get('authors', ''), 'source_digest':paper['source_sha256']}, lambda _:None)
            checks = {}
            for name in ('paper.epub','semantic.epub'):
                proc = subprocess.run(['epubcheck',str(work/name)],capture_output=True,text=True,timeout=120)
                (work/(name+'.epubcheck.log')).write_text(proc.stdout+proc.stderr)
                checks[name] = {'returncode':proc.returncode,'sha256':hashlib.sha256((work/name).read_bytes()).hexdigest()}
            record.update(status='passed' if all(c['returncode']==0 for c in checks.values()) else 'epubcheck_failed',
                          converter=document['converter'], conversion_revision=document.get('conversion_revision'), passages=len(document['passages']), report=document['report'], epubcheck=checks)
        except Exception as error:
            record.update(status='failed',error=str(error))
        record['seconds'] = round(time.monotonic()-start,1)
        with (root / '.verification/conversion-results.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            results = json.loads(output.read_text()) if output.exists() else {}
            results[identifier] = record
            staging = output.with_suffix('.tmp')
            staging.write_text(json.dumps(results,indent=2,ensure_ascii=False))
            staging.replace(output)
        print('RESULT',identifier,record['status'],record['seconds'],flush=True)
    return int(any(results.get(identifier, {}).get('status') != 'passed' for identifier in selected))


if __name__=='__main__':
    raise SystemExit(main())
