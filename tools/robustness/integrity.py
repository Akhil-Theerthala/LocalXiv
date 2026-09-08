"""Detect content changes against an independently reviewed XHTML snapshot.

A snapshot is a comparison aid, not proof that the original conversion was
correct. Review it against original source/PDF evidence before accepting it.
"""
from __future__ import annotations
import copy
import hashlib
import json
import posixpath
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET


def tag(e): return e.tag.rsplit('}',1)[-1]


def text(e):
    e=copy.deepcopy(e)
    for parent in e.iter():
        for child in list(parent):
            if tag(child) in ('annotation','script','style'):
                parent.remove(child)
    return ' '.join(''.join(e.itertext()).split())


def math_tree(e):
    # Keep operators, scripts, fractions, table structure and semantic attributes.
    return [tag(e), {k:v for k,v in sorted(e.attrib.items()) if k not in ('id','class','alttext')},
            ' '.join((e.text or '').split()),
            [math_tree(c) for c in e if tag(c) not in ('annotation','annotation-xml')]]


def snapshot(chapters: dict[str,bytes], resources: dict[str,bytes]):
    result={key:[] for key in ('prose','headings','tables','math','images','links','problems')}
    trees={name:ET.fromstring(data) for name,data in chapters.items()}
    ids={name:{e.get('id') for e in root.iter() if e.get('id')} for name,root in trees.items()}
    for name,root in trees.items():
        for e in root.iter():
            kind=tag(e)
            if kind=='p':result['prose'].append(text(e))
            if kind in ('h1','h2','h3','h4','h5','h6'):result['headings'].append([kind,text(e)])
            if kind=='table':
                result['tables'].append([[{'text':text(c),'rowspan':c.get('rowspan','1'),'colspan':c.get('colspan','1')}
                    for c in row if tag(c) in ('th','td')] for row in e.iter() if tag(row)=='tr'])
            if kind=='math':result['math'].append(math_tree(e))
            if kind not in ('a','img','object'):continue
            attr='href' if kind=='a' else 'data' if kind=='object' else 'src'
            href=e.get(attr,'');parts=urlsplit(href)
            if kind=='a':result['links'].append([text(e),href])
            if parts.scheme or parts.netloc:continue
            target=posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(parts.path))) if parts.path else name
            if target not in chapters and target not in resources:
                result['problems'].append({'kind':'missing_resource','chapter':name,'target':target})
            elif parts.fragment and target in chapters and unquote(parts.fragment) not in ids[target]:
                result['problems'].append({'kind':'missing_fragment','chapter':name,'target':href})
            if kind in ('img','object'):
                payload=resources.get(target)
                result['images'].append([e.get('alt',''),target,hashlib.sha256(payload).hexdigest() if payload is not None else None])
    return result


def compare(expected, actual):
    return {key:{'expected':expected[key],'actual':actual[key]} for key in expected if expected[key]!=actual[key]}


def read_document(work:Path):
    doc=json.loads((work/'document.json').read_text())
    chapters={c['path']:(work/c['path']).read_bytes() for c in doc['chapters']}
    resources={str(p.relative_to(work)):p.read_bytes() for p in (work/'reader').rglob('*') if p.is_file() and str(p.relative_to(work)) not in chapters}
    return snapshot(chapters,resources)
