"""Grounded visual-overview contract and PDF exports using installed tools."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from papers.overview import label, clean_citations

BENTO_PROMPT = """Stage 1: select grounded content for a research-paper bento overview.
Use the Excalidraw Visual Explainer lesson contract: a reader question, a misconception,
a central takeaway, scope, and one focal insight. These are metadata, not visible headings.
Explain the problem, relevant previous approach, what changed, how it works, supported
findings and their limits. Choose 4–9 distinct cards according to the evidence; never pad
or split a sentence simply to fill cards. Keep detailed teaching for the companion blog.
Return JSON: {"layout":"bento", "title":"reader question, <=90 characters",
"misconception":"<=200 characters", "takeaway":"<=200 characters",
"scope":"<=200 characters", "focus":0, "arrows":[], "passages":["p00001"],
"nodes":[{"title":"natural short question or heading, <=45 characters",
"body":"direct paper-specific answer, <=180 characters",
"passages":["p00001"]}]}.
focus is the zero-based index of the central insight. Every card cites exact supporting
passage IDs. Use single-line plain text without Markdown. Give every card a concise, natural heading.
Prefer paper-specific questions: what changed, why it matters, how it works, what the
evidence shows, or where it falls short. Short What? or Why? headings are fine when
the answer makes their meaning clear. Do not mechanically repeat the same questions
or put a long sentence above another long sentence. Headings and answers must work together.
Never write 'The pain point', 'What the paper did', or 'What it achieved'. Start with the
actual substance. Explain unfamiliar terms. Preserve baselines and qualifications for
numbers; do not invent results or make unsupported comparisons. A heading must frame its answer without introducing an unsupported claim.
The next stages will plan varied card sizes and render a tightly packed mosaic inspired
by dashboard bento layouts, with consistent narrow gutters and restrained colors.
Card area communicates editorial emphasis only. Do not describe geometry in the content."""


def validate_bento(spec, passages=None):
    if not isinstance(spec, dict) or spec.get('layout') != 'bento' or spec.get('arrows') != []:
        raise ValueError('Use a bento object without arrows.')
    for key, maximum in [('title',90), ('misconception',200), ('takeaway',200), ('scope',200)]:
        spec[key] = label(spec.get(key), maximum)
    nodes = spec.get('nodes')
    if not isinstance(nodes, list) or not 4 <= len(nodes) <= 9:
        raise ValueError('Select 4–9 distinct supported cards, without filler.')
    if type(spec.get('focus')) is not int or not 0 <= spec['focus'] < len(nodes):
        raise ValueError('Focus must identify one card.')
    known = {p['id'] for p in passages} if passages is not None else None
    for entry in [spec, *nodes]:
        refs = entry.get('passages')
        if not isinstance(refs, list) or not refs or any(not isinstance(r,str) or (known is not None and r not in known) for r in refs):
            raise ValueError('Every card must cite exact supporting passage IDs.')
    for card in nodes:
        card['title'] = label(card.get('title'), 45)
        if card['title'].lower().rstrip('?:.') in ('the pain point', 'what the paper did', 'what it achieved'):
            raise ValueError('Use a natural, paper-specific heading instead of a generic category label.')
        card['body'] = label(card.get('body'), 180)
        if any(term in card['body'].lower() for term in ('the pain point', 'what the paper did', 'what it achieved')):
            raise ValueError('Replace generic labels with the actual claim.')
    return spec


def plan_bento(spec, portrait=False):
    """Stage 2: pack every claim once, keeping reading order and allocating by text demand."""
    validate_bento(spec)
    rows, index = [], 0
    while index < len(spec['nodes']):
        remaining = len(spec['nodes']) - index
        count = 1 if portrait else (3 if remaining in (3, 5) else 2)
        count = min(count, remaining)
        cards = list(range(index, index + count))
        weights = [max(1, (len(spec['nodes'][i]['body']) + len(spec['nodes'][i]['title'])) / 100) + (0.7 if i == spec['focus'] else 0) for i in cards]
        rows.append({'cards': cards, 'weights': weights})
        index += count
    return dict(spec, packing={'orientation': 'portrait' if portrait else 'landscape', 'rows': rows})


def figure_source(directory, figure, extension):
    source = (directory / figure[extension]).resolve()
    if not source.is_relative_to((directory / 'reader' / 'overview-figures').resolve()) or source.suffix != '.' + extension:
        raise ValueError('Invalid figure export path.')
    return source


def export_pdf(directory, paper, kind, generation):
    if kind == 'paper':
        source = directory / 'original.pdf'
        if not source.is_file() or not source.read_bytes().startswith(b'%PDF-'):
            raise ValueError('The original PDF is unavailable. Retry importing this paper.')
        return source
    if kind == 'both':
        raise ValueError('Download the original paper and blog PDFs separately.')
    if not generation:
        raise ValueError('Generate the requested overview or blog before exporting it.')
    target = directory / ('overview.pdf' if kind == 'bento' else 'blog.pdf')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        work = Path(temporary)
        candidate = work / 'export.pdf'
        if kind == 'bento':
            source = figure_source(directory, generation['figures'][0], 'svg')
            command = ['rsvg-convert', '--format=pdf', '-o', str(candidate), str(source)]
        else:
            xelatex = shutil.which('xelatex')
            if not xelatex and Path('/Library/TeX/texbin/xelatex').is_file():
                xelatex = '/Library/TeX/texbin/xelatex'
            if not xelatex:
                raise ValueError('Blog PDF export requires XeLaTeX. Install MacTeX, then restart LocalXiv.')
            text = clean_citations(generation['text'])
            for i, figure in enumerate(generation.get('figures', [])):
                image = work / f'figure-{i}.png'
                if figure.get('png'):
                    shutil.copyfile(figure_source(directory, figure, 'png'), image)
                else:
                    subprocess.run(['rsvg-convert', '-o', str(image), str(figure_source(directory, figure, 'svg'))], check=True, capture_output=True, timeout=60)
                text = text.replace('{{figure:' + figure['id'] + '}}', f'\n\n![]({image.name})\n\n' + figure.get('caption', ''))
            # Model Markdown cannot request local files or remote images during PDF rendering.
            parsed = subprocess.run(['pandoc', '--from=markdown-raw_html-raw_tex', '--to=json'], input=text, text=True, capture_output=True, check=True, timeout=30)
            tree = json.loads(parsed.stdout)
            allowed = {f'figure-{i}.png' for i in range(len(generation.get('figures', [])))}
            def restrict_images(value):
                if isinstance(value, dict):
                    if value.get('t') == 'Image' and value['c'][2][0] not in allowed:
                        value.clear()
                        value.update(t='Str', c='[External image omitted]')
                    for child in value.values():
                        restrict_images(child)
                elif isinstance(value, list):
                    for child in value:
                        restrict_images(child)
            restrict_images(tree)
            markdown = work / 'blog.json'
            markdown.write_text(json.dumps(tree))
            command = ['pandoc', str(markdown), '--from=json', '--standalone',
                       '--pdf-engine=' + xelatex, '--pdf-engine-opt=-no-shell-escape',
                       '-V', 'geometry:margin=25mm', '-o', str(candidate)]
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=120)
        if result.returncode or not candidate.is_file() or not candidate.read_bytes().startswith(b'%PDF-'):
            raise ValueError('PDF export failed: ' + result.stderr[-1200:])
        candidate.replace(target)
    return target
