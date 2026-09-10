"""Measure old and new recovery order on the same cached development input."""
import argparse
import json
from pathlib import Path
import shutil
import time

from sample import CACHE, MANIFEST, ROOT, save
from evaluate import revision
from integrity import read_document, compare
from papers.convert import convert_import, convert_paper


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    papers = json.loads(MANIFEST.read_text())['papers']
    if not any(p['id'] == args.id and p['split'] == 'development' for p in papers):
        parser.error('Use a development paper; leave the holdout untouched')
    record = json.loads((CACHE/'downloads.json').read_text())[args.id]
    source = ROOT/record['directory']
    output = CACHE/'benchmarks'/args.name
    output.mkdir(parents=True, exist_ok=False)
    fingerprint = revision()
    report = {'id':args.id, 'code_revision':fingerprint, 'input_hashes':record['hashes'],
              'scope':'One paired cached-input run; excludes original source/PDF downloading.', 'runs':{}}
    snapshots = {}
    for variant in ('baseline', 'candidate'):
        work = output/variant
        work.mkdir()
        for name in ('source', 'original.pdf'):
            shutil.copy2(source/name, work/name)
        if (source/'arxiv-html').is_dir():
            shutil.copytree(source/'arxiv-html', work/'arxiv-html')
        start = time.monotonic()
        document = (convert_import(work, record['metadata'], lambda _: None, epub_only=True) if variant == 'candidate'
                    else convert_paper(work, record['metadata']))
        elapsed = time.monotonic()-start
        snapshots[variant] = read_document(work)
        report['runs'][variant] = {'seconds':elapsed, 'converter':document['converter'], 'attempts':document['report']['attempts']}
        save(output/'results.json', report)
        print(variant, round(elapsed,3), document['converter'], flush=True)
    report['content_changes'] = compare(snapshots['baseline'], snapshots['candidate'])
    report['code_unchanged'] = fingerprint == revision()
    report['reduction_percent'] = 100*(1-report['runs']['candidate']['seconds']/report['runs']['baseline']['seconds'])
    save(output/'results.json', report)
    return int(bool(report['content_changes']) or not report['code_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
