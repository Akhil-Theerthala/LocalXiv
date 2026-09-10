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
NARRATIVE_TIPS = """Build understanding for a technically curious reader who has not read the paper. Organize the explanation around the paper's central question. Begin with a single paragraph of one to three sentences stating the concrete pain point and why it matters. Then explain what was done previously, what those approaches enabled, and the specific gap that remained, using only the paper's account of prior work. Establish essential background before introducing this paper's method.

Explain what this paper does in detail: the mechanism, the role of each important component, how the parts fit together, and how they address the opening pain point. Anticipate questions a reader may not think to ask, especially why the authors chose X rather than a plausible Y. Distinguish reasons explicitly stated by the authors, comparisons or ablations actually tested, and interpretations grounded in the evidence. Never invent author intent, a missing experiment, or proof that an untested alternative is worse. When the paper does not explain a choice or evaluate an alternative, say so plainly. Explain relevant tradeoffs without turning the article into a list of speculative objections.

Use the shared original-figure readings to explain the paper's framework and architecture: component roles, inputs and outputs, parallel branches, repeated blocks and skip connections. State how each important original figure develops the central idea and which relationships a simplification must preserve. Then teach readers to interpret the results: axes, symbols, panels, baselines, measurements and qualifications supported by the evidence. Distinguish original figures, author explanations and generated schematics. Do not infer unseen details from captions. Choose what needs explaining before choosing a rendering template. Explain each generated figure and its simplifications alongside it.

Finish with the core insights, what the work achieved, the conditions under which the evidence supports that conclusion, and what remains unresolved. Preserve the details needed to understand the paper; avoid hype and repetitive summaries. Use a worked example only when supported by the paper, and identify any interpretation as interpretation. Do not invent background facts or anecdotes."""


def overview_preferences(settings):
    language = settings.get('overview_language', 'casual')
    length = settings.get('overview_length', 'medium')
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError('Choose casual, semi-formal, or formal blog language.')
    if not isinstance(length, str) or length not in LENGTHS:
        raise ValueError('Choose short, medium, or large blog length.')
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


def label(value, maximum=300, *, field="label"):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\n' in value:
        raise ValueError(f'{field} must be nonempty single-line text of at most {maximum} characters.')
    return value.strip()


def validate_outline(plan, passages):
    known = {p['id'] for p in passages}
    for key in ('question', 'throughline'):
        plan[key] = label(plan.get(key), 600)
    opening = plan.get('opening')
    if not isinstance(opening, list) or not 1 <= len(opening) <= 3:
        raise ValueError('Plan one to three opening sentences about the pain point.')
    plan['opening'] = [label(sentence, 400) for sentence in opening]
    sections = plan.get('sections', [])
    if not isinstance(sections, list) or not 4 <= len(sections) <= 7:
        raise ValueError('The article needs 4–7 planned sections.')
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError('Invalid article section.')
        section['heading'] = label(section.get('heading'), 100)
        section['purpose'] = label(section.get('purpose'), 600)
    roles = [section.get('role') for section in sections]
    if roles[0] != 'prior_work' or roles[-1] != 'insights' or not all(role in ('prior_work', 'method', 'evidence', 'insights') for role in roles):
        raise ValueError('Start with prior_work, explain method and evidence, and end with insights.')
    if roles.count('prior_work') != 1 or roles.count('insights') != 1 or 'method' not in roles or 'evidence' not in roles or roles != sorted(roles, key=('prior_work', 'method', 'evidence', 'insights').index):
        raise ValueError('Order sections as prior_work, method, evidence, insights.')
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
    opening = ' '.join(plan['opening'])
    if clean_citations(text).split('\n\n', 1)[0].strip() != clean_citations(opening):
        raise ValueError('Begin with the exact planned pain-point paragraph before the first heading.')
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
    if spec.get('layout') == 'illustration':
        from papers.illustrations import validate_illustration
        return validate_illustration(spec)
    if spec.get('layout') not in ('sequence', 'comparison', 'bento'):
        raise ValueError('Figure layout must be sequence, comparison, or bento.')
    nodes = spec.get('nodes', [])
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= 4 or (spec['layout'] == 'comparison' and len(nodes) != 2) or (spec['layout'] == 'bento' and len(nodes) != 3):
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
    import copy
    from papers.illustrations import render_illustration
    spec = copy.deepcopy(spec)
    if spec.get("layout") == "bento":
        from papers.bento import validate_bento, plan_bento
        validate_bento(spec)
        spec = plan_bento(spec, spec.get("packing", {}).get("orientation") == "portrait")
    else:
        validate_figure(spec)
    illustrations = ([spec] if spec.get('layout') == 'illustration' else
                     [c['visual'] for c in spec.get('nodes', []) if c.get('visual', {}).get('kind') == 'illustration'])
    for illustration in illustrations:
        illustration['_asset'] = render_illustration(directory, illustration)
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
    return {**{ext: str(relative) + '.' + ext for ext in ('svg', 'png', 'excalidraw')}, 'checks': checks}
