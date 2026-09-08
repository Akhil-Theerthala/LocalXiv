"""Freeze seeded arXiv sampling frames, then download selected documents.

Run from the repository: python3 tools/robustness/sample.py sample|download
Network operations are sequential and at least three seconds apart. Failed
requests are recorded; a retry never changes the random sample.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / '.verification/robustness'
MANIFEST = ROOT / 'docs/verification/robustness-sample.json'
SEED = 20260908
NS = {'a':'http://www.w3.org/2005/Atom', 'x':'http://arxiv.org/schemas/atom',
      'o':'http://a9.com/-/spec/opensearch/1.1/'}
last_request = 0.0


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def pause():
    global last_request
    time.sleep(max(0, 3.1 - (time.monotonic() - last_request)))
    last_request = time.monotonic()


def feed(query, start=0, count=1000):
    url = 'https://export.arxiv.org/api/query?' + urlencode(dict(
        search_query=query, start=start, max_results=count,
        sortBy='submittedDate', sortOrder='ascending'))
    path = CACHE / 'feeds' / (hashlib.sha256(url.encode()).hexdigest() + '.xml')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            try:
                pause()
                with urlopen(Request(url, headers={'User-Agent':'LocalXiv robustness evaluation'}), timeout=90) as response:
                    data = response.read(20_000_000)
                root = ET.fromstring(data)
                if root.find('o:totalResults', NS) is None:
                    raise ValueError('API did not return a results count: ' + data[:300].decode(errors='replace'))
                path.write_bytes(data)
                save(path.with_suffix('.json'), {'url':url, 'retrieved_at':datetime.now(timezone.utc).isoformat(),
                                               'sha256':hashlib.sha256(data).hexdigest()})
                break
            except Exception as error:
                print('REQUEST FAILED', attempt + 1, url, str(error), flush=True)
                if attempt == 2: raise
                delay = max(30 * (attempt + 1), int(getattr(error, 'headers', {}).get('Retry-After', '60')) if getattr(error, 'code', None) == 429 else 0)
                time.sleep(delay)
    root = ET.fromstring(path.read_bytes())
    records = []
    for e in root.findall('a:entry', NS):
        def text(name): return ' '.join((e.findtext(name, '', NS)).split())
        identifier = text('a:id').split('/abs/')[-1]
        if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[A-Za-z.-]+/\d{7})v\d+', identifier):
            raise ValueError('Unexpected arXiv identifier: ' + identifier)
        records.append({'id':identifier, 'title':text('a:title'), 'authors':'; '.join(
            a.findtext('a:name','',NS) for a in e.findall('a:author',NS)),
            'abstract':text('a:summary'), 'comment':text('x:comment'), 'journal_ref':text('x:journal_ref'),
            'published':text('a:published'), 'updated':text('a:updated'),
            'categories':[c.get('term') for c in e.findall('a:category',NS)],
            'arxiv_url':'https://arxiv.org/abs/' + identifier, 'feed':str(path.relative_to(ROOT))})
    return int(root.findtext('o:totalResults', namespaces=NS)), records


def strata():
    for venue in ('NeurIPS','ICML','ICLR','CVPR','ICCV','ECCV','ACL','EMNLP','NAACL','AAAI','IJCAI','KDD'):
        year = 2023 if venue == 'ICCV' else 2024
        yield venue, f'(co:"{venue} {year}" OR jr:"{venue} {year}")', 3, 'conference'


def sample():
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        'seed':SEED, 'created_at':datetime.now(timezone.utc).isoformat(),
        'population':'arXiv query results, not all published papers; conference membership initially author-reported',
        'sampling':'independent seeded sampling without replacement within each stratum; duplicate papers skipped before conversion',
        'strata':[], 'papers':[]}
    done = {s['name'] for s in manifest['strata']}
    seen = {re.sub(r'v\d+$','',p['id']) for p in manifest['papers']}
    for name, query, size, kind in strata():
        if name in done: continue
        print('SAMPLING', name, flush=True)
        total, _ = feed(query, count=1)
        rng = random.Random(f'{SEED}:{name}')
        record = {'name':name, 'kind':kind, 'query':query, 'population_count':total, 'requested':size}
        selected = []
        # Conference frames are small enough to save and filter the whole pool.
        pool = []
        for start in range(0, total, 500):
            _, entries = feed(query,start,500)
            pool.extend(entries)
        year = '2023' if name == 'ICCV' else '2024'
        pattern = re.compile(r'(?<![A-Za-z])' + name + r'\s*[-,\x27’]?\s*' + year + r'\b',re.I)
        pool = [p for p in pool if pattern.search(p['comment']+' '+p['journal_ref'])
                and not re.search(r'workshop|submitted to|under review|rejected',p['comment']+' '+p['journal_ref'],re.I)]
        pool.sort(key=lambda p:p['id'])
        save(CACHE/'pools'/f'{name}.json',pool)
        record['eligible_count'] = len(pool)
        ranks = rng.sample(range(len(pool)),len(pool))
        candidates = ((rank,pool[rank]) for rank in ranks)
        for rank, p in candidates:
            base = re.sub(r'v\d+$','',p['id'])
            if base in seen: continue
            p.update(stratum=name, kind=kind, sample_rank=rank, split='development')
            selected.append(p); seen.add(base)
            if len(selected)==size: break
        if len(selected)!=size: raise ValueError(f'{name}: only {len(selected)} eligible papers for {size} requested')
        holdout = 3 if kind=='notes' else 1
        for p in selected[-holdout:]: p['split']='holdout'
        record['selected_ids']=[p['id'] for p in selected]
        manifest['strata'].append(record);manifest['papers'].extend(selected)
        save(MANIFEST,manifest)
        print('SELECTED',name,[p['id'] for p in selected],flush=True)
    print('CONFERENCE SAMPLE',len(manifest['papers']),flush=True)


def download():
    from papers import acquire
    manifest = json.loads(MANIFEST.read_text())
    if not manifest.get('frozen_at'): raise ValueError('Finish sampling before downloads/conversion')
    path = CACHE/'downloads.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    original = acquire.download
    def paced(url, destination, limit=200_000_000):
        pause()
        return original(url,destination,limit)
    acquire.download=paced
    for p in manifest['papers']:
        if records.get(p['id'],{}).get('status')=='downloaded': continue
        work=CACHE/'inputs'/p['id'].replace('/','_')
        print('DOWNLOAD',p['id'],p['title'],flush=True)
        record={'id':p['id'],'directory':str(work.relative_to(ROOT))}
        try:
            metadata=acquire.acquire(p['arxiv_url'],work)
            record.update(status='downloaded', metadata=metadata,
                hashes={n:hashlib.sha256((work/n).read_bytes()).hexdigest() for n in ('source','original.pdf') if (work/n).exists()})
        except Exception as error:
            record.update(status='failed',error=str(error))
        records[p['id']]=record;save(path,records)
        print('DOWNLOAD RESULT',p['id'],record['status'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['sample','download'])
    args=parser.parse_args()
    (sample if args.action=='sample' else download)()
