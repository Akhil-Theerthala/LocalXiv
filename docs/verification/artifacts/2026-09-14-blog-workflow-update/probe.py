"""Offline Blog probe: operation, comparison, worked example, one omitted drawing.

Runs the real coordinator with a scripted provider and the native renderer, then writes the
cleaned article, the surviving figures, and an exported EPUB and PDF beside this script. It makes
no provider call. Run it from the repository root:

    .venv/bin/python docs/verification/artifacts/2026-09-14-blog-workflow-update/probe.py
"""
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
os.environ.setdefault('LOCALXIV_HTML_RENDERER', str(REPO / 'papers' / 'html-snapshot'))

from papers.ai import generate_overview  # noqa: E402
from papers.agent_overviews import candidate_digest  # noqa: E402
from papers.reading import build_orientation  # noqa: E402

OUT = Path(__file__).resolve().parent
for stale in ('reader', 'overview-export', 'article.md', 'result.json', 'overview.epub',
              'blog.pdf', 'document.json', 'generation_context.json', 'candidate.json',
              'reviews.json', 'failure.json'):
    target = OUT / stale
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()
(OUT / 'reader').mkdir()
(OUT / 'reader' / 'paper.xhtml').write_text('''<html><body>
<section id="abstract"><h1>Abstract</h1>
<p id="abs">The paper compares a frozen baseline with a learned update.</p></section>
<section id="method"><h1>1 Method</h1>
<p id="m1">An input reaches a frozen path and a learned update, whose outputs are added.</p></section>
<section id="results"><h1>2 Results</h1>
<p id="r1">The two methods rank differently on the two evaluated settings.</p></section>
<section id="worked"><h1>3 Worked example</h1>
<p id="w1">For the toy input the frozen path returns 3 and the update returns 0.5.</p></section>
<section id="scope"><h1>4 Limitations</h1>
<p id="s1">Only two datasets were tested.</p></section>
</body></html>''')

DOCUMENT = {
    'directory': str(OUT), 'title': 'A frozen baseline with a learned update',
    'arxiv_id': '2501.00099v1', 'format': 'epub', 'source_digest': 'probe-digest',
    'passages': [
        {'id': 'p00001', 'section': '1 Method', 'href': 'reader/paper.xhtml#m1',
         'text': 'An input reaches a frozen path and a learned update, whose outputs are added.'},
        {'id': 'p00002', 'section': '2 Results', 'href': 'reader/paper.xhtml#r1',
         'text': 'The two methods rank differently on the two evaluated settings.'},
        {'id': 'p00003', 'section': '3 Worked example', 'href': 'reader/paper.xhtml#w1',
         'text': 'For the toy input the frozen path returns 3 and the update returns 0.5.'},
        {'id': 'p00004', 'section': '4 Limitations', 'href': 'reader/paper.xhtml#s1',
         'text': 'Only two datasets were tested.'},
    ],
}

IDENTIFIER_LABELS = {
    'fig1': 'Two paths, one output',
    'fig2': 'Ranking across settings',
    'fig3': 'Step by step',
}


def brief(identifier, title, purpose, exit_state, construction, layout, label, caption):
    return {
        'id': identifier, 'title': title,
        'paper_connection': 'The retained paper describes this operation.',
        'caption': caption, 'illustrative': False, 'passages': ['p00001'],
        'purpose': purpose, 'entry_context': ['The prose has introduced both paths.'],
        'exit_state': exit_state, 'construction': construction, 'layout_intent': layout,
        'content': [{'text': label, 'kind': 'label', 'passages': ['p00001']}],
        'exact_text': [label], 'illustrative_values': [],
    }


BRIEFS = [
    brief('fig1', 'Two paths, one output',
          'How does an input reach the layer output?', 'The reader can trace both paths.',
          'flow', 'Input at left; frozen and trainable paths stacked in the middle; addition at right.',
          'Two paths, one output', 'The frozen path and the learned update add to one output.'),
    brief('fig2', 'Ranking across settings',
          'Which method wins in each setting?', 'The reader can state the ranking.',
          'comparison', 'The two settings side by side; the winning method marked in each.',
          'Ranking across settings', 'The ranking depends on the evaluated setting.'),
    brief('fig3', 'Step by step',
          'What does the toy input compute?', 'The reader can repeat the arithmetic.',
          'flow', 'The toy input at left; frozen 3 and update 0.5; the sum at right.',
          'Step by step', 'The worked example returns 3.5.'),
]

TEXT = ('The paper compares a frozen baseline with a small learned update [p00001].\n\n'
        'An input reaches a frozen path and a trainable path, and their outputs are added '
        '[p00001]. Follow the blue branch in the diagram below to see the addition [p00001].\n\n'
        '{{figure:fig1}}\n\n'
        'The two methods rank differently in the two evaluated settings [p00002]. '
        'The second drawing shows which method wins in each setting [p00002].\n\n'
        '{{figure:fig2}}\n\n'
        'For the toy input the frozen path returns 3 and the update returns 0.5, so the layer '
        'output is 3.5 [p00003]. The third drawing traces that computation step by step [p00003].\n\n'
        '{{figure:fig3}}\n\n'
        'Only two datasets were tested [p00004].')

PLAN = {'paper_type': 'method',
        'question': {'text': 'How does the learned update change the frozen baseline?',
                     'passages': ['p00001']},
        'contribution': {'text': 'The paper adds a small learned update to a frozen path.',
                         'passages': ['p00001']},
        'finding': {'text': 'The combined output follows from adding the two path outputs.',
                    'passages': ['p00003']},
        'limitation': {'text': 'Only two datasets were tested.', 'passages': ['p00004']},
        'visual_focus': 'The input reaches both paths and their outputs are added.',
        'relationships': [{'source': 'Input', 'target': 'Layer output',
                           'relationship': 'The two path outputs are added', 'passages': ['p00001']}]}


def action(name, **arguments):
    return {'text': '', 'tool_calls': [{'id': 'call_' + name, 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments)}}],
            'usage': {'total_tokens': 10}}


def svg(label, *, font_size=18, view_box='0 0 640 240'):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + view_box
            + '" font-family="Arial, sans-serif" font-size="' + str(font_size) + '" fill="#243b32">'
            + '<rect x="20" y="20" width="600" height="90" rx="10" fill="#dce8cf"/>'
            + '<text x="40" y="72" font-size="' + str(font_size) + '">' + label + '</text>'
            + '</svg>')


def prompt_text(messages):
    content = messages[-1]['content']
    return content[0].get('text', '') if isinstance(content, list) else content


class Scripted:
    def __init__(self):
        self.settings = {'model': 'probe-model', 'endpoint': 'https://example.test/v1',
                         'overview_language': 'semi-formal', 'overview_length': 'medium',
                         'overview_vision': False}
        self.calls = []
        self.fig2_drawings = 0
        self.fig3_drawings = 0
        self.cleanup_seen = None

    def complete(self, messages, **kwargs):
        self.calls.append(messages)
        payload = json.dumps(messages, ensure_ascii=False)
        if kwargs.get('json_object') is False:
            names = {item['function']['name'] for item in kwargs.get('tools', [])}
            if 'submit_selection' in names:
                return action('submit_selection', candidate={
                    'paper_type': 'method', 'focus': 'Explain the combined output.',
                    'section_ids': [], 'passage_ids': ['p00001', 'p00002', 'p00003', 'p00004'],
                    'figure_ids': []})
            if 'submit_plan' in names:
                return action('submit_plan', candidate=PLAN)
            if 'submit_draft' in names:
                return action('submit_draft', candidate={'plan': PLAN, 'text': TEXT,
                                                         'figures': BRIEFS})
            raise AssertionError('Unscripted authoring request')
        if 'DRAWING ASSIGNMENT' in payload:
            identifier = re.search(r'panel id: (fig\d+)', payload).group(1)
            if identifier == 'fig2':
                self.fig2_drawings += 1
                return {'text': 'not json at all', 'usage': {'total_tokens': 1}}
            if identifier == 'fig3':
                self.fig3_drawings += 1
                if self.fig3_drawings == 1:
                    return {'text': json.dumps({'panel_id': 'fig3',
                                                'svg': svg(IDENTIFIER_LABELS['fig3'], font_size=11)}),
                            'usage': {'total_tokens': 10}}
                return {'text': json.dumps({'panel_id': 'fig3',
                                            'svg': svg(IDENTIFIER_LABELS['fig3'])}),
                        'usage': {'total_tokens': 10}}
            return {'text': json.dumps({'panel_id': identifier,
                                        'svg': svg(IDENTIFIER_LABELS[identifier])}),
                    'usage': {'total_tokens': 10}}
        if 'STAGE: REVIEW' in payload:
            return {'text': json.dumps({'action': 'verdict', 'approved': True, 'issues': []}),
                    'usage': {'total_tokens': 10}}
        if 'STAGE: TEXT CORRECTION' in payload:
            article = prompt_text(messages).split('<article>\n', 1)[1].split('\n</article>', 1)[0]
            digest = re.search(r'CURRENT TEXT DIGEST: ([0-9a-f]{64})', prompt_text(messages)).group(1)
            self.cleanup_seen = (payload, article)
            self.cleanup_edits = [
                {'old': ' Follow the blue branch in the diagram below to see the addition [p00001].',
                 'new': ' Adding the two outputs gives the layer output [p00001].'},
                {'old': ' The second drawing shows which method wins in each setting [p00002].',
                 'new': ''},
            ]
            return {'text': json.dumps({'base_digest': digest, 'edits': self.cleanup_edits}),
                    'usage': {'total_tokens': 10}}
        raise AssertionError('Unscripted request: ' + payload[-300:])


def main():
    provider = Scripted()
    orientation = build_orientation(DOCUMENT)
    result = generate_overview(provider, DOCUMENT, lambda message: print('progress:', message))
    (OUT / 'article.md').write_text(result['cited_text'])
    (OUT / 'result.json').write_text(json.dumps(
        {'text': result['text'], 'cited_text': result['cited_text'],
         'figure_outcomes': result['provenance']['figure_outcomes'],
         'figure_ids': result['provenance']['reviews'][-1]['figure_ids'],
         'article_digest': result['provenance']['reviews'][-1]['article_digest'],
         'delivered_digest': candidate_digest(result['cited_text']),
         'svg_profile_revision': result['provenance']['svg_profile_revision'],
         'cleanup_edits': result['provenance']['cleanup_edits'],
         'usage_calls': len(result['provenance']['usage']),
         'provider_calls': len(provider.calls)}, indent=2, ensure_ascii=False))
    print('=== CLEANED ARTICLE ===')
    print(result['cited_text'])
    print('=== FIGURE OUTCOMES ===')
    print(json.dumps(result['provenance']['figure_outcomes'], indent=2))
    print('surviving figure assets:', [figure['id'] for figure in result['figures']])
    print('provider calls:', len(provider.calls),
          '| fig2 drawing requests:', provider.fig2_drawings,
          '| fig3 drawing requests:', provider.fig3_drawings)
    print('cleanup saw marker-free article:', '{{figure:fig2}}' not in provider.cleanup_seen[1])
    # The repair prompt for fig3 must carry the measured size, not a generic failure.
    repair = next(prompt_text(message) for message in provider.calls
                  if 'DRAWING ASSIGNMENT' in json.dumps(message) and 'measured' in json.dumps(message)
                  and 'fig3' in prompt_text(message))
    for line in repair.splitlines():
        if 'measured' in line or 'font' in line.lower():
            print('fig3 repair feedback:', line.strip()[:200])
    # Rendered survivor dimensions and measured label sizes.
    for figure in result['figures']:
        checks = figure['checks']
        labels = [(run.get('path'), round(run.get('displayed_size_px', 0), 1), run.get('text'))
                  for run in checks.get('text_runs', [])]
        print('figure', figure['id'], 'canvas', checks['canvas'], 'labels', labels)
    # Exported EPUB: only surviving figures, no omitted prose.
    from papers.document import export_overview
    epub = export_overview(OUT, DOCUMENT, result)
    with zipfile.ZipFile(epub) as archive:
        names = archive.namelist()
        xhtml = ' '.join(archive.read(name).decode() for name in names if name.endswith('.xhtml'))
    print('=== EPUB ===')
    print('fig assets:', sorted(name.split('/')[-1] for name in names if 'fig' in name.split('/')[-1]))
    words = ' '.join(re.sub('<[^>]+>', ' ', xhtml).split())
    for needle, expected in [('Adding the two outputs', True), ('blue branch', False),
                             ('second drawing', False), ('layer output is 3.5', True),
                             ('{{figure:', False), ('fig2', False)]:
        print('epub contains %-22r: %s (expected %s)' % (needle, needle in words, expected))
    ET.parse(OUT / 'overview-export' / 'reader' / 'main.xhtml')
    print('exported XHTML parses cleanly')
    print('PDF export:', end=' ')
    from papers.exports import artifact
    from papers.library import Library
    library = Library(Path(tempfile.mkdtemp()))
    paper = library.save_paper('one', dict(DOCUMENT, directory=str(OUT)), OUT)
    library.save_generation('one', 'overview', result)
    pdf = artifact(library, paper, 'overview', 'pdf')
    print(pdf.name, pdf.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
