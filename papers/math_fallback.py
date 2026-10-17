"""Recover only Pandoc's explicitly unrendered math, preserving its TeX evidence."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MATH='http://www.w3.org/1998/Math/MathML'
# A few equations that neither renderer can draw stay as visible TeX. More than this fails the route.
# ponytail: an absolute count; make it a share of the paper's equations if long papers need more.
MAX_KEPT_TEX=3


def repair_math(path:Path, macros:dict|None=None, packages:list[str]=(), definitions:list[str]=()) -> list[dict]:
    """macros, packages, and definitions come from the paper, so an expression renders as it does in LaTeX."""
    with zipfile.ZipFile(path) as book:
        infos=book.infolist()
        members={i.filename:book.read(i.filename) for i in infos}
    trees={name:ET.fromstring(data) for name,data in members.items() if name.endswith('.xhtml')}
    pending=[]
    for name,tree in trees.items():
        for parent in tree.iter():
            for e in parent:
                classes=e.get('class','').split()
                if e.tag.rsplit('}',1)[-1]!='span' or 'math' not in classes:
                    continue
                if e.find('.//{*}math') is not None:
                    continue
                if len(e):
                    raise ValueError('Unrendered math has unexpected nested content; source fallback is required.')
                pending.append((name,parent,e,{'tex':e.text or '', 'display':'display' in classes}))
    if not pending:
        raise ValueError('Pandoc warned about math but provided no isolated expression to recover.')
    node=shutil.which('node')
    if not node:
        raise ValueError('Node.js is required for the alternate equation renderer.')
    payload=[]
    for _,_,_,formula in pending:
        tex=formula['tex'].strip()
        for left,right in [('$$','$$'),('$','$'),(r'\[',r'\]'),(r'\(',r'\)')]:
            if tex.startswith(left) and tex.endswith(right) and len(tex)>=len(left)+len(right):
                tex=tex[len(left):-len(right)]
                break
        payload.append({**formula,'tex':tex})
    result=subprocess.run([node,str(Path(__file__).with_name('tex_math.js'))],
        input=json.dumps({'formulas':payload,'macros':macros or {},'packages':list(packages),
                          'definitions':list(definitions)}),
        capture_output=True,text=True,timeout=120)
    if result.returncode:
        raise ValueError('Alternate equation renderer failed: '+result.stderr[-800:])
    rendered=json.loads(result.stdout)
    rejected=[(formula,item) for (_,_,_,formula),item in zip(pending,rendered,strict=True) if item.get('error')]
    if len(rejected)>MAX_KEPT_TEX:
        formula,item=rejected[0]
        raise ValueError(f'Alternate equation renderer rejected {len(rejected)} equations, first '
                         +formula['tex'][:200]+': '+item['error'])
    repairs=[]
    for (name,parent,old,formula),item in zip(pending,rendered,strict=True):
        if item.get('error'):
            # Pandoc's span keeps the TeX as visible text. Record it in the conversion report.
            repairs.append({'chapter':name,'tex':formula['tex'],'renderer':None,'kept_as_tex':item['error']})
            continue
        math=ET.fromstring(item['mathml'])
        if math.tag!='{'+MATH+'}math' or math.find('.//{*}merror') is not None:
            raise ValueError('Alternate renderer returned invalid or unresolved math.')
        # Pandoc left the equation's \label in its TeX, so its target was lost with the unrendered span.
        labels=re.findall(r'\\label\s*\{([^{}]+)\}',formula['tex'])
        if old.get('id') or labels:
            math.set('id',old.get('id') or labels.pop(0))
        position=list(parent).index(old)
        for label in labels:
            parent.insert(position,ET.Element('{http://www.w3.org/1999/xhtml}span',{'id':label}))
            position+=1
        math.set('display','block' if formula['display'] else 'inline')
        semantics=ET.Element('{'+MATH+'}semantics')
        row=ET.SubElement(semantics,'{'+MATH+'}mrow')
        for child in list(math):
            math.remove(child)
            row.append(child)
        ET.SubElement(semantics,'{'+MATH+'}annotation',{'encoding':'application/x-tex'}).text=formula['tex']
        math.append(semantics)
        math.tail=old.tail
        parent[list(parent).index(old)]=math
        repairs.append({'chapter':name,'tex':formula['tex'],'renderer':'MathJax TeX'})
    # Every expression is drawn or recorded before any bytes in the EPUB change.
    for name in {p[0] for p in pending}:
        members[name]=ET.tostring(trees[name],encoding='utf-8',xml_declaration=True)
    staging=path.with_suffix('.repaired.epub')
    try:
        with zipfile.ZipFile(staging,'w') as book:
            for info in infos:
                book.writestr(info,members[info.filename])
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)
    path.with_suffix('.math-fallback.json').write_text(json.dumps(repairs,indent=2))
    return repairs
