"""Reuse the corpus evaluator without overwriting the previous repair evidence."""
import hashlib
import json
from pathlib import Path
import sys

from sample import CACHE, ROOT, save


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('evaluate', 'audit'):
        raise SystemExit('Usage: historical.py evaluate|audit --stage NAME [evaluation options]')
    action = sys.argv.pop(1)
    workspace = CACHE/'historical'
    papers = json.loads((ROOT/'docs/verification/corpus.json').read_text())['papers']
    original = CACHE/'original-regression/2212.10156v2'
    meta = json.loads((original/'metadata.json').read_text())
    papers.append({'id':meta['arxiv_id'], 'title':meta['title'], 'authors':meta.get('authors',''),
                   'directory':str(original.relative_to(ROOT)), 'source_file':'source', 'pdf_file':'original.pdf'})
    downloads = {}
    for paper in papers:
        identifier = paper['id']
        source = ROOT/paper['directory']
        directory = workspace/'inputs'/identifier
        directory.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for name, previous, expected in [('source',paper.get('source_file','source.tar'),paper.get('source_sha256')),
                                        ('original.pdf',paper.get('pdf_file','paper.pdf'),paper.get('pdf_sha256'))]:
            path = source/previous
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected and expected != digest:
                raise ValueError('Historical input changed: '+identifier+'/'+previous)
            target = directory/name
            if not target.exists(): target.symlink_to(path.resolve())
            if target.resolve() != path.resolve(): raise ValueError('Unexpected historical input link')
            hashes[name] = digest
        downloads[identifier] = {'status':'downloaded','directory':str(directory.relative_to(ROOT)), 'hashes':hashes,
                                 'metadata':{'arxiv_id':identifier,'title':paper['title'],'authors':paper.get('authors',''),'source_digest':hashes['source']}}
    save(workspace/'downloads.json', downloads)
    save(workspace/'manifest.json', {'frozen_at':'historical-exact-version-regressions',
         'papers':[{**p, 'split':'development', 'stratum':'original-regression' if p['id']==meta['arxiv_id'] else 'historical-repair'} for p in papers]})
    if action == 'evaluate':
        import evaluate
        evaluate.CACHE = workspace
        evaluate.MANIFEST = workspace/'manifest.json'
        return evaluate.main()
    import audit_run
    audit_run.CACHE = workspace
    return audit_run.main()


if __name__ == '__main__':
    raise SystemExit(main())
