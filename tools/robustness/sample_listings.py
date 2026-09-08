"""Add cross-disciplinary papers and notes using public monthly arXiv listings.

API requests for deep non-CS ranks failed and were rate-limited before any
non-CS selection. This alternative chooses one seeded year/month per field,
then samples uniformly from that complete monthly listing. Keep this cluster
sampling design explicit; it is not uniform sampling over all arXiv papers.
"""
import hashlib
import html
import json
import random
import re
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from sample import CACHE, ROOT, MANIFEST, SEED, save, pause


def fetch(url):
    path=CACHE/'listings'/(hashlib.sha256(url.encode()).hexdigest()+'.html')
    if not path.exists():
        pause()
        with urlopen(Request(url,headers={'User-Agent':'LocalXiv robustness evaluation'}),timeout=90) as response:
            data=response.read(10_000_000)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        save(path.with_suffix('.json'),{'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),
                                       'sha256':hashlib.sha256(data).hexdigest()})
    return path.read_text(), str(path.relative_to(ROOT))


def plain(s):return ' '.join(html.unescape(re.sub('<[^>]+>',' ',s)).split())


def parse(page,provenance):
    records=[]
    for dt,dd in re.findall(r'<dt>(.*?)</dt>\s*<dd>(.*?)</dd>',page,re.S):
        match=re.search(r'href\s*=\s*[\x22\x27]/abs/([^\x22\x27]+)',dt)
        if not match:continue
        fields={}
        for cls,value in re.findall(r'<div class=[\x22\x27](list-[^\x22\x27]+)[\x22\x27]>(.*?)</div>',dd,re.S):
            fields[cls.split()[0]]=re.sub(r'^(Title|Comments|Journal-ref|Subjects):\s*','',plain(value))
        identifier=match[1]
        records.append({'id':identifier,'title':fields['list-title'],'authors':fields.get('list-authors',''),
                        'comment':fields.get('list-comments',''),'journal_ref':fields.get('list-journal-ref',''),
                        'subjects':fields.get('list-subjects',''),'listing':provenance,
                        'arxiv_url':'https://arxiv.org/abs/'+identifier})
    return records


def pin(p):
    if re.search(r'v\d+$',p['id']):return p
    page,provenance=fetch(p['arxiv_url'])
    versions=re.findall(re.escape(p['id'])+r'v([1-9]\d*)',html.unescape(page))
    if not versions:raise ValueError('No version on abstract page for '+p['id'])
    p=dict(p, selected_base_id=p['id'], version_evidence=provenance)
    p['id']+='v'+str(max(map(int,versions)))
    p['arxiv_url']='https://arxiv.org/abs/'+p['id']
    return p


def main():
    manifest=json.loads(MANIFEST.read_text())
    if manifest.get('frozen_at'):
        print('ALREADY FROZEN',len(manifest['papers']));return
    if len([s for s in manifest['strata'] if s['kind']=='conference'])!=12:
        raise ValueError('Finish the conference sample first')
    done={s['name'] for s in manifest['strata']}
    seen={re.sub(r'v\d+$','',p['id']) for p in manifest['papers']}
    fields=[('mathematics','math'),('statistics','stat'),('condensed-matter','cond-mat'),
            ('astrophysics','astro-ph'),('high-energy-theory','hep-th'),
            ('quantitative-biology','q-bio'),('economics','econ')]
    note_pool={}
    for name,cat in fields:
        rng=random.Random(f'{SEED}:listing:{name}')
        year=rng.choice(list(range(2020,2026)));month=rng.randint(1,12)
        base=f'https://arxiv.org/list/{cat}/{year}-{month:02d}'
        page,provenance=fetch(base+'?show=2000')
        count=re.search(r'Total of\s+([\d,]+)\s+entries',page)
        if not count:raise ValueError('No monthly population count: '+base)
        total=int(count[1].replace(',',''));pool=parse(page,provenance)
        for start in range(2000,total,2000):
            page,provenance=fetch(base+f'?skip={start}&show=2000');pool.extend(parse(page,provenance))
        pool=sorted({p['id']:p for p in pool}.values(),key=lambda p:p['id'])
        if len(pool)!=total:raise ValueError(f'Listing incomplete: {base}: {len(pool)} of {total}')
        save(CACHE/'pools'/f'{name}-listing.json',pool)
        for p in pool:
            if re.search(r'\bnotes\b|\blectures?\b|\btutorial\b',p['title']+' '+p['comment'],re.I):note_pool[p['id']]=p
        if name in done:continue
        selected=[]
        for rank in rng.sample(range(total),total):
            p=pool[rank]
            if p['id'] in seen:continue
            selected.append(dict(p,stratum=name,kind='discipline',sample_rank=rank,split='development'))
            seen.add(p['id'])
            if len(selected)==4:break
        selected[-1]['split']='holdout'
        # Freeze identities before pinning versions, so a request failure cannot redraw.
        draft=CACHE/'draws'/f'{name}.json'
        if not draft.exists():save(draft,selected)
        selected=[pin(p) for p in json.loads(draft.read_text())]
        manifest['papers'].extend(selected)
        manifest['strata'].append({'name':name,'kind':'discipline','frame':base,'population_count':total,
                                  'sampling':'seeded random year/month, then uniform without replacement',
                                  'selected_ids':[p['id'] for p in selected]})
        save(MANIFEST,manifest);print('SELECTED',name,[p['id'] for p in selected],flush=True)
    if 'notes' not in done:
        pool=sorted(note_pool.values(),key=lambda p:p['id'])
        save(CACHE/'pools'/'notes-listing.json',pool)
        rng=random.Random(f'{SEED}:listing:notes');selected=[]
        for rank in rng.sample(range(len(pool)),len(pool)):
            p=pool[rank]
            if p['id'] in seen:continue
            selected.append(dict(p,stratum='notes',kind='notes',sample_rank=rank,split='development'))
            seen.add(p['id'])
            if len(selected)==12:break
        if len(selected)!=12:raise ValueError('Insufficient distinct notes')
        for p in selected[-3:]:p['split']='holdout'
        draft=CACHE/'draws'/'notes.json'
        if not draft.exists():save(draft,selected)
        selected=[pin(p) for p in json.loads(draft.read_text())]
        manifest['papers'].extend(selected)
        manifest['strata'].append({'name':'notes','kind':'notes','population_count':len(pool),
                                  'sampling':'uniform without replacement from notes/lecture/tutorial title or comment matches in the seven monthly frames',
                                  'selected_ids':[p['id'] for p in selected]})
    for p in manifest['papers']:
        if p['kind']=='conference':p['venue_track']='Findings' if 'findings' in p['comment'].lower() else 'conference, author-reported'
    manifest['sampling_amendment']='Non-CS API sampling failed before selecting papers. Monthly public listing frames were substituted with seeded year/month selection, before conversion.'
    manifest['frozen_at']=datetime.now(timezone.utc).isoformat()
    save(MANIFEST,manifest);print('FROZEN',len(manifest['papers']),flush=True)


if __name__=='__main__':main()
