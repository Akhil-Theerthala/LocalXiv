"""Resume revision-specific real conversions without changing the frozen sample."""
from __future__ import annotations
import argparse
import collections
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sample import CACHE, MANIFEST, ROOT, save


def revision(root=ROOT):
    digest=hashlib.sha256()
    for directory in ('native','papers','app'):
        for path in sorted((root/directory).rglob('*')):
            if path.suffix in ('.py','.js','.mjs','.csl'):
                digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    digest.update((root/'package-lock.json').read_bytes())
    return digest.hexdigest()


def failure_group(message):
    patterns = [('math_rendering',r'TeX math|equation|MathJax'),
                ('missing_resource',r'missing source file|figure|Could not find image|not found'),
                ('latex_syntax',r'unexpected|Undefined control sequence|undefined:'),
                ('timeout',r'timed out|exceeded.*minutes|exceeded.*limit'),
                ('content_validation',r'content|anchor|link target|bibliography'),
                ('source_archive',r'archive|TeX source')]
    return next((label for label,pattern in patterns if re.search(pattern,message,re.I)), 'other')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--split',choices=['development','holdout','all'],default='development')
    parser.add_argument('--ids',nargs='*')
    parser.add_argument('--html',action='store_true',help='Evaluate retained arXiv HTML as an independent route')
    parser.add_argument('--combined',action='store_true',help='Evaluate the application recovery order without counting PDF fallback as success')
    args=parser.parse_args()
    if args.html and args.combined: parser.error('Choose one conversion route')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.stage): parser.error('Invalid stage name')
    manifest=json.loads(MANIFEST.read_text())
    if not manifest.get('frozen_at'): parser.error('Sample is not frozen')
    downloads=json.loads((CACHE/'downloads.json').read_text())
    stage=CACHE/'runs'/args.stage
    mode='combined' if args.combined else 'html' if args.html else 'source'
    mode_file=stage/'mode.json'
    if mode_file.exists() and json.loads(mode_file.read_text())!=mode:
        parser.error('Choose a new stage for a different conversion route')
    if not mode_file.exists() and (stage/'results.json').exists() and args.html:
        parser.error('An existing source stage cannot become an HTML stage')
    code=stage/'code'
    if not code.exists():
        stage.mkdir(parents=True,exist_ok=True)
        staging=stage/('code-'+str(time.time_ns()))
        staging.mkdir()
        for name in ('native','papers','app','node_modules'):
            shutil.copytree(ROOT/name,staging/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ('package.json','package-lock.json'):
            shutil.copyfile(ROOT/name,staging/name)
        staging.rename(code)
    save(mode_file,mode)
    fingerprint=revision(code)
    sys.path.insert(0, str(code))
    spec=importlib.util.spec_from_file_location('evaluation_convert',code/'papers/convert.py')
    converter=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    if args.combined:
        from app.server import Application
        application=Application.__new__(Application)
        application.checkpoint=lambda *_: None
        def no_epub(job, directory, metadata, error, **kwargs):
            raise ValueError('EPUB unavailable; original PDF retained. '+str(error))
        application.pdf_fallback=no_epub
    if args.html:
        html_spec=importlib.util.spec_from_file_location('evaluation_html',code/'papers/arxiv_html.py')
        html_reader=importlib.util.module_from_spec(html_spec)
        html_spec.loader.exec_module(html_reader)
    result_path=stage/'results.json'
    results=json.loads(result_path.read_text()) if result_path.exists() else {}
    papers=[p for p in manifest['papers'] if (args.split=='all' or p['split']==args.split)
            and (not args.ids or p['id'] in args.ids)]
    if args.ids and set(args.ids)-{p['id'] for p in papers}: parser.error('Unknown ID or wrong split')
    for paper in papers:
        identifier=paper['id']
        previous=results.get(identifier)
        if previous and previous.get('status') not in ('running','download_unavailable'):
            if previous.get('code_revision')!=fingerprint:
                raise ValueError('Code changed; choose a new stage to preserve earlier results')
            continue
        record={'id':identifier,'title':paper['title'],'stratum':paper['stratum'],'split':paper['split'],'evaluation_mode':mode,
                'code_revision':fingerprint,'started_at':datetime.now(timezone.utc).isoformat()}
        downloads=json.loads((CACHE/'downloads.json').read_text())
        download=downloads.get(identifier,{})
        if download.get('status')!='downloaded':
            record.update(status='download_unavailable',error=download.get('error','Not downloaded yet'))
            results[identifier]=record;save(result_path,results);continue
        source=ROOT/download['directory']
        for name,digest in download['hashes'].items():
            if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Input changed: '+identifier+'/'+name)
        if revision(code)!=fingerprint: raise ValueError('Parser changed during evaluation; stop and start a new stage')
        work=stage/identifier.replace('/','_')
        if work.exists():
            # Preserve partial attempts rather than merging stale generated files.
            work.rename(work.with_name(work.name+'-interrupted-'+str(time.time_ns())))
        work.mkdir(parents=True)
        for name in ('source','original.pdf','abstract.html','metadata.json'):
            if (source/name).exists(): shutil.copyfile(source/name,work/name)
        record.update(status='running',directory=str(work.relative_to(ROOT)),source_hash=download['hashes']['source'])
        results[identifier]=record;save(result_path,results)
        print('START',identifier,paper['title'],flush=True)
        started=time.monotonic()
        conversion_started=None
        try:
            if args.html:
                record['html_cache_hit']=(source/'arxiv-html/manifest.json').exists()
                record['html_input']=html_reader.retrieve(source,download['metadata'])
                shutil.copytree(source/'arxiv-html',work/'arxiv-html')
            elif args.combined and (source/'arxiv-html').is_dir():
                shutil.copytree(source/'arxiv-html',work/'arxiv-html')
            record['retrieval_seconds']=round(time.monotonic()-started,2) if args.html else 0
            conversion_started=time.monotonic()
            if args.combined:
                try:
                    doc=converter.convert_paper(work,download['metadata'],source_engine='pandoc')
                except Exception as error:
                    doc=application.source_fallback({'id':'evaluation'},work,download['metadata'],error)
                html_manifest=work/'arxiv-html/manifest.json'
                if html_manifest.exists(): record['html_input']=json.loads(html_manifest.read_text())
            else:
                doc=converter.convert_paper(work,download['metadata'],html_only=True) if args.html else converter.convert_paper(work,download['metadata'])
            record.update(status='converted',converter=doc['converter'],report=doc['report'],
                passages=len(doc['passages']),chapters=len(doc['chapters']),
                conversion_revision=doc['conversion_revision'],
                output_hashes={n:hashlib.sha256((work/n).read_bytes()).hexdigest() for n in ('paper.epub','semantic.epub','document.json')})
        except Exception as error:
            record.update(status='failed',error=str(error),failure_group=failure_group(str(error)))
            report=work/'conversion-report.json'
            if report.exists(): record['report']=json.loads(report.read_text())
        record['seconds']=round(time.monotonic()-started,2)
        if conversion_started is not None:
            record['conversion_seconds']=round(time.monotonic()-conversion_started,2)
        if revision(code)!=fingerprint: record['status']='invalidated_code_changed'
        results[identifier]=record;save(result_path,results)
        print('RESULT',identifier,record['status'],record['seconds'],flush=True)
    print(dict(collections.Counter(r['status'] for r in results.values())),flush=True)
    return int(any(results[p['id']]['status']!='converted' for p in papers))


if __name__=='__main__':
    raise SystemExit(main())
