"""Article contracts and local SVG overview figures."""
import json
import re
import subprocess
import uuid
from pathlib import Path

PASSAGE_CITATIONS = r'\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]'
LANGUAGES = {
    'casual': 'Use approachable, conversational language, with natural contractions and concrete explanations. Keep the technical substance precise; avoid forced jokes or slang.',
    'semi-formal': 'Use polished, accessible explanatory prose. Keep a professional tone without academic stiffness.',
    'formal': 'Use precise, restrained professional language. Avoid conversational asides and contractions, but still explain unfamiliar concepts clearly.',
}
LENGTHS = {'short': 'about 750 words', 'medium': '750–1,250 words',
           'large': '1,500–2,000 words, longer only when needed to explain the paper'}
NARRATIVE_TIPS = '''Build a self-contained explanatory article, with the narrative clarity of an HBR or Economist feature. Organize around one central question and a developing answer, not the paper's section order or a list of findings. Open with the concrete problem and why it matters, using only supported context. Let each section resolve a question and prepare the next; make the transitions explicit. Introduce the background and intuition the reader needs before the mechanism, then use the evidence to test the explanation and establish its limits. Preserve enough technical detail to understand what was done, how it works, and what the results mean. Do not invent anecdotes, quotes, examples, or background facts to create a story. End by answering the opening question with the qualifications the evidence requires.'''


def overview_preferences(settings):
    language = settings.get('overview_language', 'casual')
    length = settings.get('overview_length', 'medium')
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError('Choose casual, semi-formal, or formal overview language.')
    if not isinstance(length, str) or length not in LENGTHS:
        raise ValueError('Choose short, medium, or large overview length.')
    return language, length


WRITING_TIPS = '''Write for a technically curious reader who has not read the paper. Give each section a concrete, descriptive heading and one job. Start paragraphs with their point, then explain why. Define a term before using its abbreviation. Explain intuition before equations. Keep paragraphs short, usually 2–4 sentences. Report the baseline, dataset, and qualification beside each numerical result. Distinguish uncertainty, calibration, accuracy, and refusal when relevant. Use examples only when supported by the paper, and label interpretation. End with what the evidence establishes and leaves open. Avoid hype, stock transitions, repeated summaries, and a wall of bullets.

Use Markdown throughout. Typeset inline mathematics with $...$ and display equations with $$ on separate lines; never wrap equations in code fences. Explain symbols in nearby prose. Where the paper supports a comparison across methods, assumptions, or results, include a compact Markdown table without waiting for the reader to request one. Use a header row, a pipe-separated --- delimiter row, and each data row on its own line, with the same column count. Keep math delimiters inside cells and escape literal cell pipes. Never invent results to fill a table. Preserve equations and table structure during revision.'''


def clean_citations(text):
    return re.sub(r'[ \t]*' + PASSAGE_CITATIONS, '', text)


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError('The model returned an invalid article or figure plan. Retry generation.') from None
    if not isinstance(value, dict):
        raise ValueError('The model plan must be a JSON object.')
    return value


def label(value, maximum=300):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\n' in value:
        raise ValueError('The model plan contains a missing or oversized label.')
    return value.strip()


def validate_outline(plan, passages):
    known = {p['id'] for p in passages}
    for key in ('question', 'throughline'):
        plan[key] = label(plan.get(key), 600)
    sections = plan.get('sections', [])
    if not isinstance(sections, list) or not 3 <= len(sections) <= 7:
        raise ValueError('The article needs 3–7 planned sections.')
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError('Invalid article section.')
        section['heading'] = label(section.get('heading'), 100)
        section['purpose'] = label(section.get('purpose'), 600)
    if len({s['heading'] for s in sections}) != len(sections):
        raise ValueError('Article headings must be distinct.')
    figures = plan.get('figures', [])
    if not isinstance(figures, list) or not 1 <= len(figures) <= 3:
        raise ValueError('Plan 1–3 explanatory figures.')
    for i, figure in enumerate(figures, 1):
        if not isinstance(figure, dict):
            raise ValueError('Invalid figure brief.')
        figure['id'] = 'fig' + str(i)
        for key in ('question', 'takeaway', 'brief', 'scope'):
            figure[key] = label(figure.get(key), 600)
        if figure.get('after_section') not in [s['heading'] for s in sections]:
            raise ValueError('A figure must belong to a planned section.')
        refs = figure.get('passages', [])
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or r not in known for r in refs):
            raise ValueError('A figure brief cited missing paper evidence.')
    return plan


def figure_marker(figure):
    return '{Insert figure|' + figure['id'] + '|' + figure['brief'] + '}'


def validate_article(text, plan):
    headings = re.findall(r'^#{1,2}\s+(.+?)\s*$', text, re.M)
    if headings != [s['heading'] for s in plan['sections']]:
        raise ValueError('The draft did not preserve the planned article sections. Retry generation.')
    for figure in plan['figures']:
        marker = figure_marker(figure)
        if text.count(marker) != 1 or not re.search(r'^' + re.escape(marker) + r'\s*$', text, re.M):
            raise ValueError('The draft lost a figure brief. Retry generation.')
        before = text.split(marker)[0]
        if re.findall(r'^#{1,2}\s+(.+?)\s*$', before, re.M)[-1] != figure['after_section']:
            raise ValueError('The draft placed a figure in the wrong section.')


def validate_figure(spec):
    for key, size in (('title', 90), ('takeaway', 200), ('scope', 200)):
        spec[key] = label(spec.get(key), size)
    if spec.get('layout') not in ('sequence', 'comparison'):
        raise ValueError('Figure layout must be sequence or comparison.')
    nodes = spec.get('nodes', [])
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= 4 or (spec['layout'] == 'comparison' and len(nodes) != 2):
        raise ValueError('Use 2–4 steps or exactly two comparison panels.')
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError('Invalid figure panel.')
        node['title'] = label(node.get('title'), 45)
        node['body'] = label(node.get('body'), 150)
    if type(spec.get('focus')) is not int or not 0 <= spec['focus'] < len(nodes):
        raise ValueError('Select one focal panel.')
    arrows = spec.get('arrows', [])
    if not isinstance(arrows, list) or len(arrows) != (len(nodes) - 1 if spec['layout'] == 'sequence' else 0):
        raise ValueError('Every sequence transition needs an explicit meaning; comparisons have no arrows.')
    spec['arrows'] = [label(a, 45) for a in arrows]
    return spec


def render_figure(directory, figure_id, spec):
    validate_figure(spec)
    # Unique assets keep an unsuccessful regeneration from replacing the saved article's figures.
    relative = Path('reader') / 'overview-figures' / uuid.uuid4().hex / figure_id
    output = Path(directory) / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name('overview_render.mjs')
    result = subprocess.run(['node', str(script), str(output)], input=json.dumps(spec), text=True,
                            capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError('The overview figure could not pass local rendering checks: ' + result.stderr[:1200])
    checks = json.loads(result.stdout)
    return {'svg': str(relative) + '.svg', 'checks': checks}
