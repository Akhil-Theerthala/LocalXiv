"""Restricted HTML/SVG authoring and native static exports; no model code execution."""
import base64
import html
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET

TAGS = set('div section p span strong em br h2 h3 ul ol li svg g rect circle ellipse line polyline polygon path text tspan defs marker title desc'.split())
ATTRS = set('class id role aria-label aria-labelledby viewBox width height x y x1 y1 x2 y2 cx cy r rx ry d points fill stroke stroke-width stroke-linecap stroke-linejoin stroke-dasharray font-size font-weight text-anchor dx dy opacity marker-end marker-start markerWidth markerHeight refX refY orient'.split())
CLASSES = set('columns stack note emphasis muted sage blue peach label'.split())
STYLE = '''*{box-sizing:border-box}body{margin:0;background:#fafbf7;color:#243b32;font:22px/1.45 Arial,sans-serif}main{width:960px;padding:40px}header{margin-bottom:28px}h1{font-size:38px;line-height:1.15;margin:12px 0}h2{font-size:26px}h3{font-size:23px}p{margin:12px 0}svg{display:block;width:100%;height:auto;font-family:Arial,sans-serif;font-size:20px;fill:#243b32}.columns{display:flex;gap:28px;align-items:flex-start}.columns>*{flex:1;min-width:0}.stack>*{margin-bottom:20px}.note{padding:20px;border:1px solid #dce1d8;border-radius:8px}.emphasis{font-weight:bold}.muted,.label{color:#627168}.label{font-size:16px}.sage{background:#dce8cf}.blue{background:#e1ebf1}.peach{background:#f1e3d8}footer{font-size:17px;border-top:1px solid #dce1d8;margin-top:28px;padding-top:16px}'''


def sanitize(fragment):
    if not isinstance(fragment, str) or not fragment.strip() or len(fragment) > 60000:
        raise ValueError('Figure HTML must contain 1–60000 characters.')
    fragment = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    if '<!' in fragment or '<?' in fragment:
        raise ValueError('No declarations, entities or processing instructions.')
    try:
        tree = ET.fromstring('<div>' + fragment + '</div>')
    except ET.ParseError as exc:
        raise ValueError('Use XML-compatible HTML/SVG with closed tags and escaped ampersands: ' + str(exc)) from None
    count = 0
    for element in tree.iter():
        count += 1
        if element.tag not in TAGS:
            raise ValueError('Unsupported figure tag: ' + str(element.tag))
        unsupported = set(element.attrib) - ATTRS
        if unsupported:
            raise ValueError('Unsupported attributes on ' + element.tag + ': ' + ', '.join(sorted(unsupported)))
        if set(element.get('class', '').split()) - CLASSES:
            raise ValueError('Use only the documented layout and color classes.')
        for key, value in element.attrib.items():
            if len(value)>12000 or re.search(r'javascript:|data:|https?:|file:|\\|[<>]',value,re.I):
                raise ValueError('Figure attributes cannot load resources or code.')
            if 'url(' in value.lower() and not re.fullmatch(r'url\(#[A-Za-z][\w-]*\)',value):
                raise ValueError('Only local SVG marker references are allowed.')
        if element.tag == 'svg':
            try:
                x,y,w,h=map(float,element.get('viewBox','').split())
                if (x,y)!=(0,0) or not (100<=w<=2000 and 80<=h<=2000): raise ValueError()
            except ValueError:
                raise ValueError('SVG needs viewBox="0 0 width height", dimensions 100–2000 by 80–2000.') from None
        if 'font-size' in element.attrib:
            try: size=float(element.get('font-size'))
            except ValueError: raise ValueError('SVG font-size must be a number.') from None
            if not 16<=size<=80: raise ValueError('SVG text must be 16–80px. Use fewer labels instead of shrinking text.')
    if count>500: raise ValueError('Simplify the figure to fewer than 500 elements.')
    return ET.tostring(tree, encoding='unicode', method='html')


def render(directory, figure, paper_title):
    fragment = sanitize(figure['html'])
    relative = Path('reader/overview-figures') / uuid.uuid4().hex / figure['id']
    target = Path(directory) / relative
    target.parent.mkdir(parents=True)
    esc=html.escape
    page='<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><style>'+STYLE+'</style></head><body><main>'
    page+='<header><div class="label">LOCALXIV · '+esc(paper_title)+'</div><h1>'+esc(figure['title'])+'</h1><p>'+esc(figure['paper_connection'])+'</p></header>'
    page+=fragment+'<footer><strong>'+('Illustrative example. ' if figure['illustrative'] else 'Paper-grounded diagram. ')+'</strong>'+esc(figure['caption'])+'</footer></main></body></html>'
    target.with_suffix('.html').write_text(page)
    executable=os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).with_name('html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot (see development instructions).')
    result=subprocess.run([executable,str(target.with_suffix('.html')),str(target)],capture_output=True,text=True,timeout=60)
    if result.returncode: raise ValueError('HTML rendering failed: '+result.stderr[-1000:])
    checks=json.loads(target.with_suffix('.checks.json').read_text())
    png=target.with_suffix('.png').read_bytes()
    if not png.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Renderer did not produce a PNG.')
    # Compatibility with existing SVG consumers. Editable source is HTML; this SVG embeds the static PNG.
    target.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="960" height="'+str(checks['height'])+'" viewBox="0 0 960 '+str(checks['height'])+'"><title>'+esc(figure['title'])+'</title><image width="960" height="'+str(checks['height'])+'" href="data:image/png;base64,'+base64.b64encode(png).decode()+'"/></svg>')
    return {**{ext:str(relative)+'.'+ext for ext in ('html','svg','png','pdf')},'checks':checks}
