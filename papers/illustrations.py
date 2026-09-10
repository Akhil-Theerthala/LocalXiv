"""Optional, fixed Fiziko illustrations. Model output never becomes executable code."""
import base64
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


TEMPLATE = 'attention_weighted_sum'
DESCRIPTION = ('Illustrative weights for one query: 0.6, 0.3, 0.1. '
               'Output = 0.6 v1 + 0.3 v2 + 0.1 v3. Connection widths encode weights; '
               'circles stand for value vectors, not scalar magnitudes. Scores and softmax are omitted.')
PROMPT = '''
An optional local Fiziko illustration is available. First use the original paper's figure
readings to decide what relationship needs explaining. Do not choose this merely because
the paper mentions attention: a weighted-sum illustration omits how attention chooses weights.
Use it only if the reader question is specifically about combining already weighted values.
For a bento card use visual {"kind":"illustration", "template":"attention_weighted_sum",
"caption":"Illustrative weights for one query, not measured attention.", "passages":["source ID"]}.
The fixed drawing shows v1, v2, v3 with weights 0.6, 0.3, 0.1 combining into one output.
Tube widths encode these illustrative weights. It omits score calculation and softmax.
Do not describe it as measured attention, multiple heads, or a complete Transformer.
Only choose this template when it answers the figure brief and the source supports the mechanism.
'''
BLOG_PROMPT = '''
Only when the brief specifically explains combining already weighted values, consider the local
Fiziko template: layout "illustration", template "attention_weighted_sum", title, takeaway,
scope. This standalone layout needs no nodes, focus or arrows.
It shows one query combining v1, v2, v3 using illustrative weights 0.6, 0.3, 0.1.
Connection widths encode weights. Scores and softmax are omitted. State these simplifications.
Only use this when supported by the source; it is not a multi-head or full Transformer diagram.
'''


def fiziko_path():
    if not shutil.which('mpost'):
        return None
    configured = os.environ.get('FIZIKO_MP')
    if configured:
        path = Path(configured)
        return path.resolve() if path.is_file() else None
    bundled = Path(__file__).with_name('vendor') / 'fiziko' / 'fiziko.mp'
    if bundled.is_file():
        return bundled
    if shutil.which('kpsewhich'):
        result = subprocess.run(['kpsewhich', 'fiziko.mp'], capture_output=True, text=True, timeout=5)
        path = Path(result.stdout.strip())
        if result.returncode == 0 and path.is_file():
            return path.resolve()
    return None


def validate_illustration(spec):
    if spec.get('template') != TEMPLATE:
        raise ValueError('Unknown illustration template.')
    spec['alt'] = DESCRIPTION
    return spec


def render_illustration(directory, spec):
    validate_illustration(spec)
    library = fiziko_path()
    if library is None:
        raise ValueError('Fiziko rendering requires mpost and fiziko.mp via TeX or FIZIKO_MP.')
    source = '''outputformat := "svg"; outputtemplate := "%j.svg";
input fiziko.mp;
randomseed := 42;
beginfig(1);
path p;
for i := 0 upto 2:
  p := (100,220-80i){right} .. {right}(420,140);
  draw tube.l(p)(if i=0: 12 elseif i=1: 6 else: 2 fi);
endfor;
for i := 0 upto 2:
  draw sphere.c(32) shifted (84,220-80i);
endfor;
draw sphere.c(32) shifted (440,140);
setbounds currentpicture to (0,0)--(600,0)--(600,280)--(0,280)--cycle;
endfig;
end.
'''
    digest = hashlib.sha256(library.read_bytes() + source.encode() + DESCRIPTION.encode() + b'labels-v3').hexdigest()[:24]
    output = Path(directory) / 'reader' / 'overview-figures' / ('fiziko-' + digest)
    output.mkdir(parents=True, exist_ok=True)
    svg_path, png_path = output / 'illustration.svg', output / 'illustration.png'
    if not svg_path.exists() or not png_path.exists():
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            shutil.copyfile(library, work / 'fiziko.mp')
            (work / 'illustration.mp').write_text(source)
            result = subprocess.run(['mpost', '-interaction=nonstopmode', '-halt-on-error', '-restricted',
                                     'illustration.mp'], cwd=work, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise ValueError('Fiziko could not render its template: ' + (result.stdout + result.stderr)[-1200:])
            root = ET.fromstring((work / 'illustration.svg').read_text())
            root.insert(0, ET.Element('{http://www.w3.org/2000/svg}rect',
                                     {'width':'600', 'height':'280', 'fill':'white'}))
            for x, y, value in [(30,66,'v1'), (30,146,'v2'), (30,226,'v3'),
                                (145,45,'0.6'), (145,130,'0.3'), (145,200,'0.1'),
                                (465,146,'output'), (60,270,'Example weights, not measured')]:
                node = ET.SubElement(root, '{http://www.w3.org/2000/svg}text',
                                     {'x':str(x), 'y':str(y), 'font-family':'Arial', 'font-size':'30', 'fill':'#292d23'})
                node.text = value
            svg = ET.tostring(root)
            png = subprocess.run(['rsvg-convert', '--zoom=2'], input=svg, capture_output=True, check=True, timeout=30).stdout
            svg_path.write_bytes(svg)
            png_path.write_bytes(png)
            (output / 'illustration.mp').write_text(source)
    return {'svg': 'data:image/svg+xml;base64,' + base64.b64encode(svg_path.read_bytes()).decode(),
            'png': 'data:image/png;base64,' + base64.b64encode(png_path.read_bytes()).decode(),
            'width':600, 'height':280, 'alt':DESCRIPTION, 'renderer':'fiziko',
            'source':str((output / 'illustration.mp').relative_to(directory))}
