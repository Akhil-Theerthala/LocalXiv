"""Parser corpus test: convert frozen arXiv papers of many templates and say what broke and why.

Design: docs/superpowers/specs/2026-09-25-parser-corpus-test-design.md
Run from the repository root:
    python3 tools/robustness/corpus.py discover | freeze | fetch
    python3 tools/robustness/corpus.py run --tier gate --base main
    python3 tools/robustness/corpus.py explain ID | reduce ID
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import namedtuple
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent)]
import audit  # noqa: E402
import integrity  # noqa: E402
import sample  # noqa: E402
from evaluate import revision  # noqa: E402
from native import host  # noqa: E402
from papers import acquire  # noqa: E402
from papers.convert import convert_paper, sandbox_profile  # noqa: E402

CACHE = ROOT / '.verification/parser-corpus'
MANIFEST = ROOT / 'docs/verification/parser-corpus.json'
ALLOW = ROOT / 'docs/verification/parser-corpus-allow.json'
SEED = 20260925
# arxiv.org answers 406 to Python clients for sources it has not cached. The export host serves programs.
EXPORT = 'https://export.arxiv.org/'
sample.CACHE = CACHE
save = sample.save


def safe(identifier):
    return identifier.replace('/', '_')


# Templates and traits

STYLE_TEMPLATES = [
    (r'neurips_\d+|nips_?\d+', 'neurips'), (r'iclr\d+_conference', 'iclr'), (r'icml\d+', 'icml'),
    (r'colm\d+_conference', 'colm'), (r'tmlr', 'tmlr'), (r'jmlr2e', 'jmlr2e'),
    (r'acl|acl_natbib|acl\d+|naaclhlt\d+|emnlp\d+', 'acl'), (r'cvpr|iccv|wacv', 'cvpr'), (r'aaai\d*', 'aaai'),
    (r'ijcai\d+', 'ijcai'), (r'interspeech\w*', 'interspeech'), (r'spconf', 'spconf'), (r'usenix\w*', 'usenix'),
    (r'jheppub', 'jhep'), (r'jcappub', 'jcap'), (r'econometrica', 'econometrica'),
]
CLASS_TEMPLATES = [
    (r'aastex\d*', 'aastex'), (r'siamart\d*', 'siamart'), (r'lipics(?:-v\d+)?', 'lipics'),
    (r'frontiers\w*', 'frontiers'), (r'mdpi', 'mdpi'), (r'copernicus\w*', 'copernicus'), (r'elife\w*', 'elife'),
    (r'plos\w*', 'plos'), (r'tufte-\w+', 'tufte'), (r'scr(?:artcl|book|reprt)', 'koma'), (r'ctex\w+', 'ctex'),
    (r'apa[67]', 'apa'), (r'sn-jnl', 'sn-jnl'), (r'svjour3?', 'svjour3'),
]
EXERCISE_PACKAGES = {'exercise', 'exsheets', 'xsim', 'answers', 'exam'}
# Traits for the open risks in docs/parser-audit-2026-09-25.md, by risk number.
RISKS = {'algpseudocode': 1, 'cref-theorem': 1, 'ding-table': 2, 'colon-math-heading': 3,
         'listing-math-commands': 4, 'non-utf8': 5, 'unused-tex': 6, 'boxed-eqnarray': 7,
         'commented-table-split': 11}


def template_of(document_class, options, packages):
    for pattern, name in STYLE_TEMPLATES:
        if any(re.fullmatch(pattern, package, re.I) for package in packages):
            return name
    base = document_class.rsplit('/', 1)[-1]
    for pattern, name in CLASS_TEMPLATES:
        if re.fullmatch(pattern, base, re.I):
            return name
    if base == 'IEEEtran':
        return 'IEEEtran-' + next((o for o in ('conference', 'compsoc') if o in options), 'journal')
    if base == 'acmart':
        return 'acmart-' + next((o for o in options if o in ('sigconf', 'acmsmall', 'manuscript')), 'other')
    return base


def read_sources(directory):
    """Every TeX-like file as text, and the files that are not UTF-8."""
    texts, non_utf8 = {}, []
    for path in sorted(directory.rglob('*')):
        if path.suffix.lower() in ('.tex', '.sty', '.cls', '.bbl', '.bib') and path.is_file():
            relative = str(path.relative_to(directory))
            raw = path.read_bytes()
            try:
                texts[relative] = raw.decode('utf-8')
            except UnicodeDecodeError:
                texts[relative] = raw.decode('latin-1')
                non_utf8.append(relative)
    return texts, non_utf8


def include_depth(root, masked):
    def children(name):
        for target in re.findall(r'\\(?:input|include|subfile)\s*\{([^{}]+)\}', masked.get(name, '')):
            path = os.path.normpath(os.path.join(os.path.dirname(root), target.strip()))
            yield path if path.endswith('.tex') else path + '.tex'

    def depth(name, seen):
        return max((1 + depth(child, seen | {child}) for child in children(name) if child not in seen), default=0)
    return depth(root, {root})


def traits_of(files, texts, non_utf8, masked, root, packages, is_tar):
    active = '\n'.join(masked.values())
    raw = '\n'.join(v for k, v in texts.items() if k.endswith('.tex'))
    checks = {
        'algpseudocode': 'algpseudocode' in packages and re.search(r'\\(?:Function|Procedure|Statex|Call)\b', active),
        'cref-theorem': re.search(r'\\[cC]ref\s*\{', active) and re.search(r'\\newtheorem|multline', active),
        'ding-table': re.search(r'\\(?:ding|Checkmark|checkmark|XSolidBrush)\b', active)
                      and re.search(r'\\begin\{tabular', active),
        'colon-math-heading': re.search(r'\\(?:sub)*section\*?\s*\{[^{}\n]*:\s*\$', active),
        'listing-math-commands': re.search(r'\\begin\{(verbatim|lstlisting|minted)\}(?:(?!\\end\{\1\}).)*?'
                                           r'\\(?:vphantom|notag)', raw, re.S),
        'non-utf8': non_utf8,
        'unused-tex': any(re.search(r'\\documentclass', v) for k, v in masked.items() if k != root),
        'boxed-eqnarray': re.search(r'\\begin\{(eqnarray|alignat)\*?\}(?:(?!\\end\{\1).)*?\\boxed', active, re.S),
        'commented-table-split': re.search(r'%\s*\\end\{table\*?\}', raw) and re.search(r'%\s*\\begin\{table', raw),
        'bbl-only': any(f.endswith('.bbl') for f in files) and not any(f.endswith('.bib') for f in files),
        'biblatex': 'biblatex' in packages,
        'readme-json': any(Path(f).name == '00README.json' for f in files),
        'single-file': not is_tar,
        'deep-input': include_depth(root, masked) >= 3,
        'eps-figures': any(f.lower().endswith(('.eps', '.ps')) for f in files),
        'heavy-macros': len(re.findall(r'\\(?:newcommand|renewcommand|def|DeclareMathOperator)\b', active)) > 100,
        'tikz': packages & {'tikz', 'pgfplots'},
        'tikz-cd-or-xy': packages & {'tikz-cd', 'xy', 'xypic'},
        'shipped-style': any(f.endswith(('.sty', '.cls')) for f in files),
        'long-tables': re.search(r'\\begin\{(?:longtable|sidewaystable)', active),
        'algorithm2e': 'algorithm2e' in packages,
        'siunitx-columns': 'siunitx' in packages and re.search(r'\\begin\{tabular\}\s*\{[^{}]*S', active),
        'latex209': re.search(r'\\documentstyle', active),
        'minted': 'minted' in packages,
        'exercises': packages & EXERCISE_PACKAGES,
    }
    return sorted(name for name, found in checks.items() if found)


def classify(source_file, entry):
    raw = source_file.read_bytes()
    record = {key: entry.get(key) for key in ('id', 'title', 'comment', 'journal_ref', 'categories', 'published')}
    record.update(source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw))
    if raw.startswith(b'%PDF'):
        return {**record, 'template': 'pdf', 'class': None, 'traits': ['pdf-only']}
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / 'source'
        try:
            host.extract_source(source_file, directory)
            root = str(host.find_root_tex(directory).relative_to(directory))
        except host.ConversionError as error:
            return {**record, 'template': None, 'error': str(error)}
        files = [str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()]
        texts, non_utf8 = read_sources(directory)
    masked = {k: host._searchable_tex_source(v) for k, v in texts.items() if k.endswith('.tex')}
    active = '\n'.join(masked.values())
    match = re.search(r'\\document(?:class|style)\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}', masked.get(root, ''))
    if not match:
        return {**record, 'template': None, 'error': 'No \\documentclass in the root file'}
    options = [o.strip() for o in (match[1] or '').split(',')]
    packages = {name.strip() for command in ('usepackage', 'RequirePackage')
                for value in host._command_values(active, command) for name in value.split(',') if name.strip()}
    record.update(root=root, **{'class': match[2].strip()}, options=[o for o in options if o],
                  template=template_of(match[2].strip(), options, packages), packages=sorted(packages),
                  traits=traits_of(files, texts, non_utf8, masked, root, packages, tarfile.is_tarfile(source_file)))
    return record


# Quotas

Quota = namedtuple('Quota', 'name group count match queries')


def T(*names):
    return lambda c: c.get('template') in names


def category(template_names, *prefixes):
    return lambda c: c.get('template') in template_names and any(
        x.startswith(prefixes) for x in c.get('categories') or [])


def words(pattern):
    return lambda c: re.search(pattern, (c.get('title') or '') + ' ' + (c.get('comment') or ''), re.I)


def trait(name):
    return lambda c: name in c.get('traits', [])


def old(query, first, last):
    return f'{query} AND submittedDate:[{first}01010000 TO {last}12312359]'


ML, LV, ACM, OCS = ('Machine learning venues', 'Language and vision venues', 'ACM and IEEE', 'Other CS publishers')
MATH, PHYS, LIFE = 'Mathematics', 'Physics and astronomy', 'Life and social sciences'
LONG, LANG, PDF = 'Long documents and teaching', 'Other languages', 'No usable source'
QUOTAS = [
    Quota('neurips', ML, 2, T('neurips'), ['co:"NeurIPS 2024"', 'co:"NeurIPS 2023"']),
    Quota('iclr', ML, 2, T('iclr'), ['co:"ICLR 2025"', 'co:"ICLR 2024"']),
    Quota('icml', ML, 2, T('icml'), ['co:"ICML 2024"', 'co:"ICML 2025"']),
    Quota('jmlr2e', ML, 1, T('jmlr2e'), ['jr:"Journal of Machine Learning Research"']),
    Quota('tmlr', ML, 1, T('tmlr'), ['jr:"Transactions on Machine Learning Research"', 'co:TMLR']),
    Quota('colm', ML, 1, T('colm'), ['co:"COLM 2024"', 'co:"COLM 2025"']),
    Quota('acl', LV, 2, T('acl'), ['co:"ACL 2024"', 'co:"EMNLP 2024"']),
    Quota('cvpr', LV, 2, T('cvpr'), ['co:"CVPR 2024"', 'co:"ICCV 2023"']),
    Quota('llncs', LV, 1, T('llncs'), ['co:"ECCV 2024"', 'co:"MICCAI 2024"']),
    Quota('aaai', LV, 1, T('aaai'), ['co:"AAAI 2025"', 'co:"AAAI 2024"']),
    Quota('ijcai', LV, 1, T('ijcai'), ['co:"IJCAI 2024"']),
    Quota('acmart-sigconf', ACM, 2, T('acmart-sigconf'), ['co:"KDD 2024"', 'co:"SIGIR 2024"']),
    Quota('acmart-acmsmall', ACM, 1, T('acmart-acmsmall'), ['jr:"ACM Transactions"', 'co:TOSEM']),
    Quota('acmart-other', ACM, 1, T('acmart-manuscript', 'acmart-other'), ['co:"CHI 2024"', 'co:"CSCW"']),
    Quota('sig-alternate', ACM, 1, T('sig-alternate', 'sig-alternate-05-2015'),
          [old('co:SIGMOD', 2010, 2015), old('co:KDD', 2010, 2015)]),
    Quota('IEEEtran-conference', ACM, 1, T('IEEEtran-conference'), ['co:"INFOCOM 2024"', 'co:GLOBECOM']),
    Quota('IEEEtran-journal', ACM, 1, T('IEEEtran-journal'), ['jr:"IEEE Transactions on Signal Processing"']),
    Quota('IEEEtran-compsoc', ACM, 1, T('IEEEtran-compsoc'), ['jr:"IEEE Transactions on Pattern Analysis"']),
    Quota('ieeeconf', ACM, 1, T('ieeeconf'), ['co:"ICRA 2024"', 'co:"IROS 2024"']),
    Quota('spconf', ACM, 1, T('spconf'), ['co:"ICASSP 2024"', 'co:"ICASSP 2025"']),
    Quota('lipics', OCS, 1, T('lipics'), ['co:ICALP', 'co:LIPIcs']),
    Quota('eptcs', OCS, 1, T('eptcs'), ['jr:EPTCS']),
    Quota('usenix', OCS, 1, T('usenix'), ['co:"USENIX Security"']),
    Quota('svjour3', OCS, 1, T('svjour3'), ['jr:"Empirical Software Engineering"', 'jr:"Journal of Optimization"']),
    Quota('sn-jnl', OCS, 1, T('sn-jnl'), ['jr:"Scientific Reports"', 'co:"Springer Nature"']),
    Quota('elsarticle', OCS, 1, T('elsarticle'), ['jr:"Pattern Recognition"', 'jr:Neurocomputing']),
    Quota('siamart', OCS, 1, T('siamart'), ['jr:"SIAM J"']),
    Quota('interspeech', OCS, 1, T('interspeech'), ['co:"Interspeech 2024"']),
    Quota('amsart', MATH, 3, T('amsart'), ['cat:math.AG', 'cat:math.NT', 'cat:math.GT']),
    Quota('amsproc', MATH, 1, T('amsproc'), ['co:"Contemporary Mathematics"', 'co:proceedings AND cat:math.RT']),
    Quota('amsbook', MATH, 1, T('amsbook'), ['co:monograph AND cat:math.AG', 'ti:"lecture notes" AND cat:math.AT']),
    Quota('article-math', MATH, 2, category({'article'}, 'math.'), ['cat:math.AP', 'cat:math.PR', 'cat:math.OC']),
    Quota('imsart', MATH, 1, T('imsart'), ['jr:"Annals of Statistics"', 'cat:math.ST']),
    Quota('smfart', MATH, 1, T('smfart'), ['co:French AND cat:math.AG']),
    Quota('diagrams', MATH, 1, trait('tikz-cd-or-xy'), ['cat:math.CT', 'cat:math.AT']),
    Quota('revtex4-1', PHYS, 1, T('revtex4-1'), ['jr:"Phys. Rev. Lett."', 'jr:"Phys. Rev. B"']),
    Quota('revtex4-2', PHYS, 2, T('revtex4-2'), ['jr:"Phys. Rev. D"', 'jr:"Phys. Rev. Lett."']),
    Quota('aastex', PHYS, 2, T('aastex'), ['jr:"Astrophys. J."', 'jr:ApJ']),
    Quota('mnras', PHYS, 2, T('mnras'), ['jr:MNRAS']),
    Quota('aa', PHYS, 1, T('aa'), ['jr:"Astron. Astrophys."', 'jr:A&A']),
    Quota('jhep', PHYS, 1, T('jhep'), ['jr:JHEP']),
    Quota('iopart', PHYS, 1, T('iopart'), ['jr:"J. Phys. A"', 'jr:"New J. Phys."']),
    Quota('pos', PHYS, 1, T('PoS'), ['co:"Proceedings of Science"', 'jr:PoS']),
    Quota('quantumarticle', PHYS, 1, T('quantumarticle'), ['jr:Quantum']),
    Quota('scipost', PHYS, 1, T('SciPost'), ['jr:"SciPost Phys."']),
    Quota('jcap', PHYS, 1, T('jcap'), ['jr:JCAP']),
    Quota('plos', LIFE, 1, T('plos'), ['jr:"PLoS Comput"', 'jr:"PLOS ONE"']),
    Quota('elife', LIFE, 1, T('elife'), ['jr:eLife']),
    Quota('frontiers', LIFE, 1, T('frontiers'), ['jr:"Frontiers in"']),
    Quota('mdpi', LIFE, 1, T('mdpi'), ['jr:Entropy', 'jr:"Remote Sensing"']),
    Quota('copernicus', LIFE, 1, T('copernicus'), ['jr:"Atmos. Chem. Phys."', 'jr:"Geosci. Model Dev."']),
    Quota('apa', LIFE, 2, T('apa'), ['cat:q-bio.NC AND abs:psychology', 'cat:cs.HC AND abs:psychological']),
    Quota('econ', LIFE, 2, category({'article'}, 'econ.', 'q-fin.'), ['cat:econ.EM', 'cat:econ.GN', 'cat:q-fin.GN']),
    Quota('stats', LIFE, 1, category({'article'}, 'stat.'), ['cat:stat.ME', 'cat:stat.AP']),
    Quota('achemso', LIFE, 1, T('achemso'), ['jr:"J. Phys. Chem."', 'jr:"J. Chem. Theory"']),
    Quota('jss', LIFE, 1, T('jss'), ['jr:"Journal of Statistical Software"']),
    Quota('thesis', LONG, 2, lambda c: T('report')(c) and words('thesis|dissertation')(c),
          ['ti:thesis', 'co:"PhD thesis"']),
    Quota('book', LONG, 1, T('book'), ['ti:textbook', 'co:book AND ti:introduction']),
    Quota('memoir', LONG, 1, T('memoir'), ['ti:dissertation', 'co:"PhD thesis"']),
    Quota('koma', LONG, 2, T('koma'), ['co:German', 'ti:Vorlesung']),
    Quota('lecture-notes', LONG, 3, words(r'lecture notes|lectures|tutorial|course'),
          ['ti:"lecture notes"', 'co:"lecture notes"', 'ti:tutorial']),
    Quota('beamer', LONG, 1, T('beamer'), ['co:slides', 'ti:slides']),
    Quota('tufte', LONG, 1, T('tufte'), ['ti:handout', 'co:"tufte"']),
    Quota('long-survey', LONG, 1, words(r'\b[1-9]\d{2} pages'), ['ti:survey AND co:"100 pages"', 'ti:survey']),
    Quota('minted-tutorial', LONG, 1, trait('minted'), ['ti:tutorial AND cat:cs.PL', 'ti:tutorial AND cat:cs.SE']),
    Quota('exercises', LONG, 1, trait('exercises'), ['ti:exercises', 'ti:"problem set"']),
    Quota('chinese', LANG, 1, T('ctex'), ['co:Chinese']),
    Quota('french', LANG, 1, lambda c: 'french' in ' '.join(c.get('options', [])), ['co:French']),
    Quota('german', LANG, 1, lambda c: re.search('german', ' '.join(c.get('options', [])), re.I),
          ['co:German']),
    Quota('russian', LANG, 1, lambda c: 'russian' in ' '.join(c.get('options', [])), ['co:Russian']),
    Quota('pdf-only', PDF, 2, trait('pdf-only'), ['cat:physics.gen-ph', 'cat:math.GM']),
]
TRAIT_NEED = 2
TRAIT_QUERIES = [old('cat:hep-th', 1996, 1999), old('cat:cond-mat', 1997, 1999), old('cat:astro-ph', 1997, 1999),
                 'co:"NeurIPS 2024"', 'jr:"Phys. Rev."', 'co:"ACL 2024"', 'cat:cs.LG', 'cat:math.CO']


# Discovery, freeze, fetch

def discover(budget, misses_allowed):
    path = CACHE / 'candidates.json'
    state = json.loads(path.read_text()) if path.exists() else {'candidates': {}, 'misses': {}, 'feeds': {}}
    candidates, misses = state['candidates'], state['misses']
    downloads = 0

    def unseen(queries):
        for query in queries:
            if query not in state['feeds']:
                try:
                    _, entries = sample.feed(query, 0, 40)
                except Exception as error:
                    print('QUERY FAILED', query, error, flush=True)
                    entries = []
                state['feeds'][query] = entries
                save(path, state)
            for entry in state['feeds'][query]:
                if entry['id'] not in candidates:
                    return entry
        return None

    def download(entry):
        nonlocal downloads
        directory = CACHE / 'candidates' / safe(entry['id'])
        directory.mkdir(parents=True, exist_ok=True)
        try:
            sample.pause()
            acquire.download(EXPORT + 'src/' + entry['id'], directory / 'source', 60_000_000)
            record = classify(directory / 'source', entry)
        except Exception as error:
            record = {'id': entry['id'], 'template': None, 'error': str(error)[:300]}
        downloads += 1
        candidates[entry['id']] = record
        save(path, state)
        print('CANDIDATE', entry['id'], record.get('template'), ','.join(record.get('traits', [])), flush=True)
        return record

    wanted = [(q.name, q.count, q.match, q.queries) for q in QUOTAS]
    wanted += [('trait:' + name, TRAIT_NEED, trait(name), TRAIT_QUERIES) for name in RISKS]
    while downloads < budget:
        progress = False
        for name, count, match, queries in wanted:
            if sum(1 for c in candidates.values() if match(c)) >= count or misses.get(name, 0) >= misses_allowed:
                continue
            entry = unseen(queries)
            if entry is None:
                continue
            progress = True
            if not match(download(entry)):
                misses[name] = misses.get(name, 0) + 1
            if downloads >= budget:
                break
        if not progress:
            break
    save(path, state)
    short = [name for name, count, match, _ in wanted if sum(1 for c in candidates.values() if match(c)) < count]
    print('DOWNLOADS', downloads, 'CANDIDATES', len(candidates), 'SHORT', short, flush=True)


def freeze():
    state = json.loads((CACHE / 'candidates.json').read_text())
    # Classify again from the cached sources, so the current trait rules decide the corpus.
    for identifier, record in state['candidates'].items():
        source = CACHE / 'candidates' / safe(identifier) / 'source'
        if source.exists():
            state['candidates'][identifier] = classify(source, record)
    pool = sorted((c for c in state['candidates'].values() if c.get('template')), key=lambda c: c['id'])
    chosen, shortfalls = {}, []

    def pick(name, group, count, matches, reason):
        rng = random.Random(f'{SEED}:{name}')
        picked = rng.sample(matches, min(count, len(matches)))
        for c in picked:
            chosen[c['id']] = {**c, 'quota': name, 'group': group, 'reason': reason,
                               'expected_route': 'pdf' if c['template'] == 'pdf' else 'pandoc'}
        if len(picked) < count:
            shortfalls.append({'quota': name, 'wanted': count, 'found': len(picked)})

    for q in QUOTAS:
        pick(q.name, q.group, q.count, [c for c in pool if q.match(c) and c['id'] not in chosen],
             'template quota ' + q.name)
    for name, risk in [(name, RISKS.get(name)) for name in sorted({t for c in pool for t in c['traits']} | set(RISKS))]:
        have = sum(1 for c in chosen.values() if name in c['traits'])
        if have < TRAIT_NEED:
            pick('trait:' + name, 'Traits', TRAIT_NEED - have,
                 [c for c in pool if name in c['traits'] and c['id'] not in chosen],
                 f'trait {name}' + (f', audit risk #{risk}' if risk else ''))
    gate = set()
    for group in dict.fromkeys(c['group'] for c in chosen.values()):
        gate.add(min(i for i, c in chosen.items() if c['group'] == group))
    for name in RISKS:
        if not any(name in chosen[i]['traits'] for i in gate):
            gate.update(sorted(i for i, c in chosen.items() if name in c['traits'])[:1])
    papers = [{'id': i, 'title': c['title'], 'class': c['class'], 'template': c['template'], 'group': c['group'],
               'traits': c['traits'], 'categories': c.get('categories'), 'reason': c['reason'],
               'expected_route': c['expected_route'], 'source_sha256': c['source_sha256'],
               'tier': 'gate' if i in gate else 'full'} for i, c in sorted(chosen.items())]
    save(MANIFEST, {'seed': SEED, 'frozen_at': datetime.now(timezone.utc).isoformat(),
                    'design': 'docs/superpowers/specs/2026-09-25-parser-corpus-test-design.md',
                    'candidates_downloaded': len(state['candidates']), 'shortfalls': shortfalls, 'papers': papers})
    print('FROZEN', len(papers), 'papers,', len(gate), 'in the gate tier; shortfalls:',
          ', '.join(f"{s['quota']} {s['found']}/{s['wanted']}" for s in shortfalls) or 'none')


def fetch():
    original = acquire.download

    def paced(url, destination, limit=200_000_000):
        sample.pause()
        return original(url.replace('https://arxiv.org/', EXPORT), destination, limit)
    acquire.download = paced
    mismatched = []
    for paper in json.loads(MANIFEST.read_text())['papers']:
        directory = CACHE / 'inputs' / safe(paper['id'])
        if not (directory / 'metadata.json').exists() or not (directory / 'source').exists():
            print('FETCH', paper['id'], flush=True)
            acquire.acquire('https://arxiv.org/abs/' + paper['id'], directory)
        if hashlib.sha256((directory / 'source').read_bytes()).hexdigest() != paper['source_sha256']:
            mismatched.append(paper['id'])
    if mismatched:
        raise SystemExit('arXiv returned different source bytes for: ' + ', '.join(mismatched))


# Conversion

CONVERT = r'''
import concurrent.futures, json, shutil, sys, time
from pathlib import Path
from papers.convert import convert_import
inputs, out, jobs, ids = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
def one(identifier):
    work, source = out / identifier.replace('/', '_'), inputs / identifier.replace('/', '_')
    if (work / 'result.json').exists():
        return
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for name in ('source', 'original.pdf', 'abstract.html', 'metadata.json'):
        if (source / name).exists():
            shutil.copyfile(source / name, work / name)
    if (source / 'arxiv-html').is_dir():
        shutil.copytree(source / 'arxiv-html', work / 'arxiv-html')
    started, result = time.monotonic(), {}
    try:
        metadata = json.loads((work / 'metadata.json').read_text())
        result['converter'] = convert_import(work, metadata, lambda _: None, epub_only=True)['converter']
    except Exception as error:
        result['error'] = str(error)[-4000:]
    result['seconds'] = round(time.monotonic() - started, 1)
    if (work / 'arxiv-html/manifest.json').exists() and not (source / 'arxiv-html').is_dir():
        shutil.copytree(work / 'arxiv-html', source / 'arxiv-html')
    (work / 'result.json').write_text(json.dumps(result))
    print(identifier, result.get('converter', 'no EPUB'), result['seconds'], flush=True)
with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
    list(pool.map(one, ids))
'''


def convert(code, out, papers, jobs):
    """Convert with the parser in `code`, in its own process, so a base checkout never mixes modules."""
    out.mkdir(parents=True, exist_ok=True)
    save(out / 'revision.json', {'code': str(code), 'revision': revision(code)})
    subprocess.run([sys.executable, '-c', CONVERT, str(CACHE / 'inputs'), str(out), str(jobs),
                    *[p['id'] for p in papers]], cwd=code, check=True,
                   env={**os.environ, 'PYTHONPATH': str(code), 'LOCALXIV_PASS_TRACE': '1'})


def worktree(reference):
    commit = subprocess.run(['git', 'rev-parse', reference], cwd=ROOT, capture_output=True, text=True,
                            check=True).stdout.strip()
    path = CACHE / 'worktrees' / commit[:12]
    if not path.exists():
        subprocess.run(['git', 'worktree', 'add', '--detach', str(path), commit], cwd=ROOT, check=True,
                       capture_output=True)
        (path / 'node_modules').symlink_to(ROOT / 'node_modules')
    return path


# Attribution

STAGES = [('extract', r' (?:extract_source|safe_extract)$'), ('root', r' find_root_tex$'), ('pass', r' prepare_\w+$'),
          ('math', r' repair_math$|math_fallback'), ('document', r'^papers/document\.py'),
          ('validate', r' (?:validate_epub|_finalize_epub|_repair_cross_file_fragments|_validate_\w+)$'),
          ('pandoc', r' convert_source$'), ('latexml', r'^papers/worker\.py:\d+ (?:run|latexml)$'),
          ('arxiv-html', r'arxiv_html')]


def stage_of(raised_at):
    return next((name for name, pattern in STAGES if re.search(pattern, raised_at or '')), 'unknown')


def blame_line(trace, relative, line):
    """Find the TeX pass that wrote a prepared line, like `git blame` with one commit per pass."""
    versions = [d for d in sorted(trace.iterdir()) if (d / relative).is_file()]
    if not versions:
        return {}

    def lines(version):
        return (version / relative).read_text(encoding='utf-8', errors='replace').splitlines()
    newer_lines, index = lines(versions[-1]), line - 1
    if index >= len(newer_lines):
        return {'location': f'{relative}:{line}', 'blame': None}
    result = {'location': f'{relative}:{line}', 'prepared': newer_lines[index].strip()[:300]}
    for newer, older in zip(reversed(versions), reversed(versions[:-1])):
        older_lines = lines(older)
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, older_lines, newer_lines, autojunk=False).get_opcodes():
            if j1 <= index < j2:
                break
        if tag != 'equal':
            return {**result, 'blame': newer.name.split('-', 1)[1],
                    'before_pass': '\n'.join(line.strip() for line in older_lines[i1:i2])[:500]}
        index, newer_lines = i1 + index - j1, older_lines
    return {**result, 'blame': 'author', 'original': f'{relative}:{index + 1}'}


def pandoc_blame(attempt):
    log = attempt / 'legacy.pandoc.log'
    errors = re.findall(r'Error at "([^"]+)" \(line (\d+), column (\d+)\):\n(.*)(?:\n(expecting .*))?',
                        log.read_text(errors='replace') if log.exists() else '')
    if not errors:
        return {}
    name, line, column, message, expecting = errors[-1]
    result = {'pandoc_error': ' '.join(filter(None, [message, expecting])), 'column': int(column)}
    if 'end of input' in message:
        return {**result, 'blame': None,
                'hint': 'An environment or group never closes. Pandoc names only the end of the file. Run explain.'}
    source = attempt / 'source'
    matches = [p for p in source.rglob(Path(name).name) if str(p).endswith(name.removeprefix('./'))]
    if len(matches) != 1 or not (attempt / 'pass-trace').is_dir():
        return {**result, 'location': f'{name}:{line}'}
    return {**result, **blame_line(attempt / 'pass-trace', str(matches[0].relative_to(source)), int(line))}


def locate(tokens, directory, limit=3):
    """Lines in the author's source that contain a token from an error message."""
    found = []
    if not directory.is_dir():
        return found
    for path in sorted(directory.rglob('*.tex')):
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if any(token in line for token in tokens):
                found.append(f'{path.relative_to(directory)}:{number}: {line.strip()[:160]}')
    exact = [f for f in found if any('{' + token + '}' in f for token in tokens)]
    definitions = [f for f in exact or found if re.search(r'\\(?:label|newcommand|def|newenvironment)\b', f)]
    return (definitions or exact or found)[:limit]


def output_elements(tokens, reader):
    """Elements in the converter output whose id is a token from the error, such as a duplicated label."""
    found = []
    for path in sorted(reader.rglob('*.xhtml')) if reader.is_dir() else []:
        text = path.read_text(encoding='utf-8', errors='replace')
        for token in tokens:
            found += [f'{path.relative_to(reader)}: <{tag} id="{token}">'
                      for tag in re.findall(r'<(\w+)[^>]*\bid="' + re.escape(token) + '"', text)]
    return found[:6]


def cause_of(work, attempt):
    cause = {'engine': attempt['engine'], 'error': attempt.get('error', '')[:800], 'raised_at': attempt.get('raised_at')}
    failed = next((p for p in attempt.get('passes', []) if 'error' in p), None)
    if failed:
        cause.update(stage='pass', blame=failed['pass'], error=failed['error'][:800])
    else:
        cause['stage'] = stage_of(cause['raised_at'])
    directory = work / attempt['engine']
    if cause['stage'] == 'pandoc' and attempt['engine'] == 'pandoc':
        cause.update(pandoc_blame(directory))
    tokens = re.findall(r'\\[A-Za-z@]{2,}|[\w.-]+:[\w:.-]+', cause['error'].splitlines()[0] if cause['error'] else '')
    if tokens:
        cause['source_lines'] = locate(tokens[:3], directory / 'pass-trace/00-original')
        cause['output_elements'] = output_elements(tokens[:3], directory / 'reader')
    return cause


def signature(cause):
    text = (cause.get('pandoc_error') or cause.get('error') or '').splitlines()
    text = re.sub(r'[\w.-]+:[\w:.-]+', 'LABEL', text[0] if text else '')
    text = re.sub(r'\d+', 'N', re.sub(r'"[^"]*"|\S+\.(?:tex|sty|cls|bib)\b', 'FILE', text))
    who = cause.get('blame') if cause.get('stage') == 'pass' else (cause.get('raised_at') or '').split(' ')[-1]
    return f"{cause.get('stage')} | {who} | {text[:120]}"


# Checks

INLINE_ONLY = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th'}
SKIPPED_TEXT = {'math', 'code', 'pre', 'script', 'style', 'annotation', 'annotation-xml'}
INVARIANTS = {'raw-tex': re.compile(r'\\[A-Za-z]{2,}'), 'unresolved-reference': re.compile(r'\?\?'),
              'replacement-character': re.compile('\ufffd'), 'raw-math': re.compile(r'\$[^$\s][^$\n]{0,80}\$')}


def invariants(work, document):
    found = collections.defaultdict(list)

    def check(text, chapter):
        for kind, pattern in INVARIANTS.items():
            if text and (match := pattern.search(text)):
                found[kind].append(f"{chapter}: ...{text[max(0, match.start() - 40):match.end() + 40].strip()}...")

    def walk(element, chapter, skipped, inline_only):
        kind = integrity.tag(element)
        if kind == 'math' and element.get('display') == 'block' and inline_only:
            found['display-math-inline'].append(f'{chapter}: <{inline_only}> holds display math: '
                                                f'{integrity.text(element)[:80]}')
        skipped = skipped or kind in SKIPPED_TEXT
        inline_only = inline_only or (kind if kind in INLINE_ONLY else None)
        if not skipped:
            check(element.text, chapter)
        for child in element:
            walk(child, chapter, skipped, inline_only)
            if not skipped:
                check(child.tail, chapter)
    for chapter in document['chapters']:
        walk(ET.parse(work / chapter['path']).getroot(), chapter['path'], False, None)
    for problem in integrity.read_document(work)['problems']:
        found['broken-link'].append(f"{problem['chapter']}: {problem['kind']} {problem['target']}")
    if not any('abstract' in p.get('section', '').lower() for p in document['passages']):
        found['no-abstract'].append('No passage belongs to an Abstract section.')
    return dict(found)


def anchor_location(anchor, directory):
    wanted = anchor.split()[:6]
    for path in sorted(directory.rglob('*.tex')) if directory.is_dir() else []:
        owners, words_ = [], []
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            for word in audit.normalized(audit.prose(line)).split():
                words_.append(word)
                owners.append(number)
        for start in (i for i, w in enumerate(words_) if w == wanted[0]):
            if words_[start:start + len(wanted)] == wanted:
                return f'{path.relative_to(directory)}:{owners[start]}'
    return None


def retention(paper, work):
    entry = audit.audit({'id': paper['id'], 'title': paper['title'], 'directory': str(CACHE / 'inputs' / safe(paper['id'])),
                         'source_file': 'source', 'pdf_file': 'original.pdf'}, work)
    original = work / 'pandoc/pass-trace/00-original'
    details = {'source_pdf_prose_anchors_missing': entry.get('missing_reader_anchor_examples', []),
               'source_pdf_caption_anchor_missing': entry.get('missing_caption_anchors', []),
               'source_pdf_note_anchor_missing': [n['anchor'] for n in entry.get('missing_note_anchors', [])],
               'source_pdf_abstract_anchor_missing': entry.get('missing_abstract_anchors', []),
               'source_pdf_table_text_missing': entry.get('missing_table_text_anchors', []),
               'braced_bibliography_fragment_missing': entry.get('missing_bibliography_fragments', []),
               'empty_figure': entry.get('reader', {}).get('empty_figures', [])}
    findings = []
    for flag in entry.get('flags', []):
        examples = []
        for item in details.get(flag, [])[:5]:
            text = item['text'] if isinstance(item, dict) and 'text' in item else item
            where = anchor_location(text, original) if isinstance(text, str) else None
            examples.append(f'{where}: {text}' if where else json.dumps(text, ensure_ascii=False)[:200])
        findings.append({'kind': 'retention', 'key': 'retention:' + flag, 'count': len(details.get(flag, [])),
                         'examples': examples})
    counts = {k: entry.get(side, {}).get(k) for side in ('source',) for k in
              ('headings', 'display_math_environments', 'figures', 'tables', 'compiled_bibliography_items')}
    counts.update({'reader_' + k: entry.get('reader', {}).get(k) for k in
                   ('headings', 'mathml', 'figures', 'tables', 'bibliography_items', 'equation_layout_tables')})
    return findings, counts, entry.get('reader_anchor_coverage')


def snapshot(work, document, counts):
    result = integrity.read_document(work)
    result['abstract'] = [p['text'] for p in document['passages'] if 'abstract' in p.get('section', '').lower()]
    result['counts'] = [[key, value] for key, value in sorted(counts.items())]
    return result


def analyze(paper, work):
    result = json.loads((work / 'result.json').read_text())
    report_path = work / 'conversion-report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    route = result.get('converter') or ('pdf' if 'EPUB unavailable' in result.get('error', '') else 'none')
    entry = {'id': paper['id'], 'title': paper['title'], 'template': paper['template'], 'group': paper['group'],
             'traits': paper['traits'], 'expected_route': paper['expected_route'], 'route': route,
             'seconds': result['seconds'], 'work': str(work.relative_to(ROOT)), 'findings': []}
    if route != paper['expected_route']:
        attempt = next((a for a in report.get('attempts', []) if a['engine'] == paper['expected_route']), None)
        cause = cause_of(work, attempt) if attempt else {'stage': 'unknown', 'error': result.get('error', '')[:800]}
        entry['findings'].append({'kind': 'route', 'key': 'route:' + signature(cause), **cause})
    document_path = work / 'document.json'
    if document_path.exists():
        document = json.loads(document_path.read_text())
        found, counts, entry['anchor_coverage'] = retention(paper, work) if (work / 'original.pdf').exists() else ([], {}, None)
        entry['findings'] += found
        for kind, examples in invariants(work, document).items():
            entry['findings'].append({'kind': 'invariant', 'key': 'invariant:' + kind, 'count': len(examples),
                                      'examples': examples[:3]})
        save(work / 'snapshot.json', snapshot(work, document, counts))
    return entry


# Comparison and report

def first_difference(old, new, path=()):
    if isinstance(old, list) and isinstance(new, list):
        for index, (a, b) in enumerate(zip(old, new)):
            if a != b:
                return first_difference(a, b, path + (index,))
        if len(old) != len(new):
            return path + (min(len(old), len(new)),), old[len(new):][:2], new[len(old):][:2]
    return path, old, new


def diff_snapshots(old, new):
    items = []
    for key in sorted(old.keys() | new.keys()):
        a = [json.dumps(x, ensure_ascii=False) for x in old.get(key, [])]
        b = [json.dumps(x, ensure_ascii=False) for x in new.get(key, [])]
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for offset in range(i2 - i1):
                    path, before, after = first_difference(json.loads(a[i1 + offset]), json.loads(b[j1 + offset]))
                    items.append({'key': key, 'item': [i1 + offset, *path], 'old': before, 'new': after})
            elif tag != 'equal':
                items.append({'key': key, 'item': [i1], 'change': tag,
                              'old': [json.loads(x) for x in a[i1:i2][:3]], 'new': [json.loads(x) for x in b[j1:j2][:3]]})
    return items


def compare(candidate, base, candidate_out, base_out):
    allowed = json.loads(ALLOW.read_text()) if ALLOW.exists() else []
    for identifier, entry in candidate.items():
        before = base.get(identifier, {'findings': []})
        known = {f['key'] for f in before['findings']}
        for finding in entry['findings']:
            finding['status'] = 'known' if finding['key'] in known else 'new'
        now = {f['key'] for f in entry['findings']}
        entry['fixed'] = sorted(known - now)
        old_path, new_path = base_out / safe(identifier) / 'snapshot.json', candidate_out / safe(identifier) / 'snapshot.json'
        if base_out != candidate_out and old_path.exists() and new_path.exists():
            changes = diff_snapshots(json.loads(old_path.read_text()), json.loads(new_path.read_text()))
            for change in changes:
                change['allowed'] = any(a['id'] == identifier and a['key'] == change['key'] and a['new'] == change['new']
                                        for a in allowed)
            entry['changes'] = changes
    return candidate


def new_problems(entry):
    return ([f for f in entry['findings'] if f['status'] == 'new']
            + [c for c in entry.get('changes', []) if not c['allowed']])


def write_report(out, results, head, base_revision):
    save(out / 'report.json', {'revision': head, 'base_revision': base_revision, 'papers': results})
    groups = collections.defaultdict(collections.Counter)
    causes = collections.defaultdict(list)
    for entry in results.values():
        row = groups[entry['group']]
        row['papers'] += 1
        row['expected route' if entry['route'] == entry['expected_route'] else
            'no EPUB' if entry['route'] in ('pdf', 'none') else 'other route'] += 1
        for kind in ('retention', 'invariant'):
            row[kind] += any(f['kind'] == kind for f in entry['findings'])
        row['regression'] += bool(entry.get('changes'))
        row['new'] += bool(new_problems(entry))
        for finding in entry['findings']:
            if finding['kind'] == 'route':
                causes[finding['key'].removeprefix('route:')].append(f"{entry['id']} ({entry['template']})")
    columns = ['papers', 'expected route', 'other route', 'no EPUB', 'retention', 'invariant', 'regression', 'new']
    lines = [f'# Parser corpus run {head[:12]}', '',
             f'Base revision {base_revision[:12] if base_revision else "none"}. '
             f'{sum(bool(new_problems(e)) for e in results.values())} of {len(results)} papers have new problems.', '',
             '## Template groups by outcome', '', '| Group | ' + ' | '.join(columns) + ' |',
             '|---|' + '---:|' * len(columns)]
    lines += [f'| {group} | ' + ' | '.join(str(row[c]) for c in columns) + ' |' for group, row in sorted(groups.items())]
    lines += ['', '## Route failures grouped by cause', '']
    for cause, papers in sorted(causes.items(), key=lambda item: -len(item[1])):
        lines += [f'- `{cause}`: {len(papers)} papers. {", ".join(papers)}']
    lines += ['', '## Papers with findings', '']
    for entry in results.values():
        if not entry['findings'] and not entry.get('changes'):
            continue
        lines += [f"### {entry['id']} {entry['template']}", '', '```text',
                  f"title    {entry['title'][:100]}", f"traits   {', '.join(entry['traits']) or 'none'}",
                  f"route    expected {entry['expected_route']}, actual {entry['route']}, {entry['seconds']} s"]
        for f in entry['findings']:
            lines.append(f"{f['status']:<8} {f['key']}")
            for field in ('raised_at', 'pandoc_error', 'location', 'blame', 'before_pass', 'prepared', 'original',
                          'hint'):
                if f.get(field):
                    lines.append(f"         {field:<12} {str(f[field]).replace(chr(10), ' / ')[:300]}")
            if f['kind'] == 'route' and not f.get('pandoc_error'):
                lines.append(f"         {'error':<12} {f['error'].splitlines()[0][:300] if f['error'] else ''}")
            lines += [f"         {'source':<12} {line}" for line in f.get('source_lines', [])]
            lines += [f"         {'output':<12} {line}" for line in f.get('output_elements', [])]
            lines += [f"         {'example':<12} {example[:300]}" for example in f.get('examples', [])]
        for change in entry.get('changes', [])[:20]:
            lines.append(f"{'allowed' if change['allowed'] else 'changed':<8} {change['key']} {change['item']}: "
                         f"{json.dumps(change['old'], ensure_ascii=False)[:140]} -> "
                         f"{json.dumps(change['new'], ensure_ascii=False)[:140]}")
        lines += [f"fixed    {key}" for key in entry.get('fixed', [])]
        lines += [f"logs     {entry['work']}", '```', '']
    (out / 'report.md').write_text('\n'.join(lines) + '\n')


def selected(tier, ids):
    papers = json.loads(MANIFEST.read_text())['papers']
    return [p for p in papers if (tier == 'full' or p['tier'] == 'gate') and (not ids or p['id'] in ids)]


def run(tier, base, ids, jobs):
    papers = selected(tier, ids)
    head = revision(ROOT)
    out = CACHE / 'runs' / head[:12]
    convert(ROOT, out, papers, jobs)
    if revision(ROOT) != head:
        raise SystemExit('The parser changed during the run. Run it again.')
    results = {p['id']: analyze(p, out / safe(p['id'])) for p in papers}
    base_results, base_out, base_revision = {}, out, None
    if base:
        code = worktree(base)
        base_revision = revision(code)
        base_out = CACHE / 'runs' / base_revision[:12]
        if base_out != out:
            convert(code, base_out, papers, jobs)
        base_results = {p['id']: analyze(p, base_out / safe(p['id'])) for p in papers}
    results = compare(results, base_results, out, base_out)
    write_report(out, results, head, base_revision)
    problems = sum(bool(new_problems(e)) for e in results.values())
    print(f'{problems} of {len(results)} papers have new problems. Report: {(out / "report.md").relative_to(ROOT)}')
    return int(problems > 0)


# Explain and reduce

def latest_work(identifier):
    work = CACHE / 'runs' / revision(ROOT)[:12] / safe(identifier)
    if not (work / 'result.json').exists():
        raise SystemExit(f'Run the corpus with --ids {identifier} first.')
    return work


def explain(identifier):
    """Convert again once for each pass that changed the source, with that pass skipped."""
    work = latest_work(identifier)
    report = json.loads((work / 'conversion-report.json').read_text())
    attempt = next(a for a in report['attempts'] if a['engine'] == 'pandoc')
    results = []
    for name in [p['pass'] for p in attempt.get('passes', [])]:
        trial = CACHE / 'explain' / safe(identifier) / name
        shutil.rmtree(trial, ignore_errors=True)
        trial.mkdir(parents=True)
        for file in ('source', 'metadata.json'):
            shutil.copyfile(CACHE / 'inputs' / safe(identifier) / file, trial / file)
        os.environ.update(LOCALXIV_SKIP_PASS=name, LOCALXIV_PASS_TRACE='1')
        try:
            convert_paper(trial, json.loads((trial / 'metadata.json').read_text()), source_engine='pandoc')
            outcome = {'pass': name, 'converts': True}
        except Exception:
            skipped_report = json.loads((trial / 'conversion-report.json').read_text())['attempts'][-1]
            outcome = {'pass': name, 'converts': False, 'cause': signature(cause_of(trial, skipped_report))}
        finally:
            del os.environ['LOCALXIV_SKIP_PASS']
        results.append(outcome)
        print(f"{name:<40} {'CONVERTS' if outcome['converts'] else 'fails: ' + outcome['cause']}", flush=True)
    save(CACHE / 'explain' / safe(identifier) / 'explain.json', results)
    suspects = [r['pass'] for r in results if r['converts']]
    print('Suspects:', ', '.join(suspects) if suspects else 'none. Skipping one pass never makes the paper convert.')


PASS_CHECK = r'''
import inspect, sys
from pathlib import Path
from native import host
source, function = Path(sys.argv[1]), getattr(host, sys.argv[2])
root = host.find_root_tex(source)
names = list(inspect.signature(function).parameters)
if names[0] != 'source_dir':
    arguments, options = (root,), {}
else:
    arguments = (source, root) if names[1:2] == ['root'] else (source,)
    options = {'compilation_dir': root.parent} if 'compilation_dir' in names else {}
try:
    function(*arguments, **options)
except Exception as error:
    print((type(error).__name__ + ': ' + str(error)).splitlines()[0])
'''


def ddmin(items, fails):
    """Delta debugging: remove chunks of lines while the same failure remains."""
    chunks = 2
    while len(items) >= 2:
        size = max(1, len(items) // chunks)
        for start in range(0, len(items), size):
            trial = items[:start] + items[start + size:]
            if fails(trial):
                items, chunks = trial, max(chunks - 1, 2)
                break
        else:
            if chunks >= len(items):
                break
            chunks = min(len(items), chunks * 2)
    return items


def reduce(identifier):
    """Shrink the file that fails to the smallest set of lines that fails the same way."""
    work = latest_work(identifier)
    report = json.loads((work / 'conversion-report.json').read_text())
    cause = cause_of(work, next(a for a in report['attempts'] if a['engine'] == 'pandoc'))
    attempt = work / 'pandoc'
    with tempfile.TemporaryDirectory(dir=CACHE) as temporary:
        source = Path(temporary) / 'source'
        shutil.copytree(attempt / 'source', source)
        profile = Path(temporary) / 'check.sb'
        profile.write_text(sandbox_profile(Path(temporary), ROOT))
        root = host.find_root_tex(source)
        if cause['stage'] == 'pass':
            # Restore the source as the failing pass received it.
            for version in sorted((attempt / 'pass-trace').iterdir()):
                shutil.copytree(version, source, dirs_exist_ok=True)
            command = [sys.executable, '-c', PASS_CHECK, str(source), cause['blame']]
            expected = cause['error'].splitlines()[0]
            targets = sorted(source.rglob('*.tex'), key=lambda p: -p.stat().st_size)
        elif cause.get('location') and cause.get('pandoc_error'):
            command = [shutil.which('pandoc'), str(root), '--from=latex', '--to=html5', '-o', os.devnull]
            expected = cause['pandoc_error'].split(' expecting ')[0]
            targets = [source / cause['location'].rsplit(':', 1)[0]]
        else:
            raise SystemExit(f"reduce needs a pass error or a located Pandoc error. This paper has: {signature(cause)}")
        environment = {**os.environ, 'PYTHONPATH': str(ROOT)}

        def fails():
            result = subprocess.run(['sandbox-exec', '-f', str(profile), *command], cwd=root.parent, env=environment,
                                    capture_output=True, text=True, timeout=120)
            return expected in result.stdout + result.stderr
        if not fails():
            raise SystemExit('The failure does not reproduce outside the full conversion. Use explain instead.')
        out = CACHE / 'reduced' / safe(identifier)
        shutil.rmtree(out, ignore_errors=True)
        for target in targets:
            original = target.read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)

            def still_fails(lines, target=target):
                target.write_text(''.join(lines), encoding='utf-8')
                return fails()
            kept = ddmin(original, still_fails)
            target.write_text(''.join(kept), encoding='utf-8')
            relative = target.relative_to(source)
            (out / relative).parent.mkdir(parents=True, exist_ok=True)
            (out / relative).write_text(''.join(kept), encoding='utf-8')
            print(f'{relative}: {len(original)} lines -> {len(kept)} lines', flush=True)
    print(f'Expected failure: {expected}\nReduced files: {out.relative_to(ROOT)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    found = commands.add_parser('discover', help='download candidate sources and record their templates')
    found.add_argument('--budget', type=int, default=400, help='most sources to download in this run')
    found.add_argument('--misses', type=int, default=12, help='non-matching downloads before a quota stops')
    commands.add_parser('freeze', help='choose the corpus from the candidates and write the manifest')
    commands.add_parser('fetch', help='download the frozen corpus and check the source hashes')
    runner = commands.add_parser('run', help='convert the corpus and report new problems')
    runner.add_argument('--tier', choices=['gate', 'full'], default='gate')
    runner.add_argument('--base', default='main', help='git reference to compare with; empty to skip')
    runner.add_argument('--ids', nargs='*')
    runner.add_argument('--jobs', type=int, default=4)
    for name in ('explain', 'reduce'):
        commands.add_parser(name).add_argument('id')
    args = parser.parse_args()
    if args.command == 'discover':
        return discover(args.budget, args.misses)
    if args.command in ('freeze', 'fetch'):
        return globals()[args.command]()
    if args.command == 'run':
        return run(args.tier, args.base, args.ids, args.jobs)
    return globals()[args.command](args.id)


if __name__ == '__main__':
    raise SystemExit(main())
