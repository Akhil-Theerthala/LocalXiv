"""Deterministic provider responses; no credentials or network calls."""
import json
import re
from papers.overview import figure_marker

PLAN = {'question': 'When can we trust model confidence?',
    'throughline': 'Explain why confidence needs checking, how to compare it with outcomes, and what the evidence establishes.',
    'sections': [
    {'heading': 'What the experiment asks', 'purpose': 'Explain the problem.'},
    {'heading': 'How the comparison works', 'purpose': 'Explain the mechanism.'},
    {'heading': 'What the result establishes', 'purpose': 'Report the limits.'}],
    'figures': [{'id': 'fig1', 'question': 'How is confidence checked?',
                 'takeaway': 'Compare confidence with observed correctness.',
                 'brief': 'Compare stated confidence with observed correctness; show why a confident answer can still be wrong.',
                 'scope': 'Conceptual comparison, not a measured effect.',
                 'after_section': 'How the comparison works', 'passages': ['p00001']}]}
SPEC = {'title': 'Confidence needs an outcome check', 'layout': 'comparison',
        'nodes': [{'title': 'Stated confidence', 'body': 'A model strongly favors an answer.'},
                  {'title': 'Observed correctness', 'body': 'Check whether answers are correct across many examples.'}],
        'focus': 1, 'arrows': [], 'takeaway': 'A confident answer alone does not establish correctness.',
        'scope': 'Conceptual comparison; panel sizes encode no measured quantity.'}
ARTICLE = '\n\n'.join('# ' + s['heading'] + '\n\nThe result is 91 percent, with $x=1$ [p00001].' +
                       ('\n\n' + figure_marker(PLAN['figures'][0]) if i == 1 else '') for i, s in enumerate(PLAN['sections']))

def response(messages, **kwargs):
    prompt = messages[-1]['content']
    if prompt.startswith('ARTICLE PLAN.'):
        text = json.dumps(PLAN)
    elif prompt.startswith(('FIGURE DESIGN.', 'FIGURE REVIEW.')):
        text = json.dumps(SPEC)
    elif prompt.startswith(('Write a self-contained', 'Check every numerical', 'Shorten this article')):
        text = ARTICLE
    else:
        ref = re.findall(r'\[(p\d+)\]', prompt)[0]
        text = 'Supported result [' + ref + '].'
    return {'text': text, 'usage': {'total_tokens': 42}}
