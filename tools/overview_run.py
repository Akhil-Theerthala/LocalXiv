"""Generate an Overview or a Blog for one library paper with any provider and model, without saving it.

Usage, from the repository root with the renderer built:

    .venv/bin/python tools/overview_run.py --paper "Attention" --model deepseek-flash
    .venv/bin/python tools/overview_run.py --paper "Attention" --provider gemini --model gemini-2.5-pro
    .venv/bin/python tools/overview_run.py --paper "Attention" --provider openrouter --model google/gemini-2.5-pro
    .venv/bin/python tools/overview_run.py --paper "PRO" --provider custom --endpoint """ \
"""http://localhost:11434/v1 --model qwen3

``--provider`` picks the base URL: deepseek (the default), gemini (Google AI Studio), openrouter,
openai, claude, or custom with ``--endpoint``. The API key is read from ``.env`` at the repository
root under the provider's usual name (DEEPSEEK_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
OPENAI_API_KEY, ANTHROPIC_API_KEY), or the name given with ``--api_key``, then from the Keychain
entry the app saved for that endpoint. The run writes only under the paper's
reader/overview-figures/ directory and prints requests, tokens, seconds, density, and the PNG
path. It never touches the saved Overview. ``--library DIR`` reads the paper from another library,
such as the isolated one app.server creates with ``--data-dir``. Repeat ``--model`` to compare models on one provider.
``--out DIR`` copies each run's PNG and editable SVG there as ``{provider}_{paper}.png`` and
``.svg`` (with ``_{model}`` appended when one invocation compares several models); a later run
with the same name replaces the file. Without ``--out`` the files stay in the library.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papers.ai import REASONING_EFFORTS, Provider  # noqa: E402
from papers.blog_workflow import generate as generate_blog  # noqa: E402
from papers.overview_workflow import generate as generate_overview  # noqa: E402
from papers.settings import get_key  # noqa: E402

PROVIDERS = {
    'deepseek': ('https://api.deepseek.com', 'DEEPSEEK_API_KEY'),
    'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/', 'GEMINI_API_KEY'),
    'openrouter': ('https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY'),
    'openai': ('https://api.openai.com/v1', 'OPENAI_API_KEY'),
    'claude': ('https://api.anthropic.com/v1', 'ANTHROPIC_API_KEY'),
    'custom': (None, 'LOCALXIV_API_KEY'),
}
ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path.home() / 'Library/Application Support/LocalXiv/library'


def load(paper_title, library=LIBRARY):
    db = sqlite3.connect(Path(library) / 'library.sqlite3')
    try:
        # A new library has no settings row until the app saves one.
        row = db.execute('select value from settings').fetchone()
        settings = json.loads(row[0]) if row else {}
        papers = [json.loads(row[0]) for row in db.execute('select value from papers')]
    finally:
        db.close()
    matches = [paper for paper in papers if paper_title.lower() in paper.get('title', '').lower()]
    if len(matches) != 1:
        raise SystemExit('Paper filter matched ' + str(len(matches)) + ' papers: '
                         + ', '.join(paper.get('title', '')[:50] for paper in matches))
    return settings, matches[0]


def api_key(endpoint, name):
    """The key named in .env or the environment, else the app's Keychain entry for the endpoint."""
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    key = values.get(name)
    if key:
        return key
    try:
        key = get_key(endpoint)
    except Exception:  # noqa: BLE001 - a missing Keychain entry reads as no key
        key = None
    if not key:
        raise SystemExit('No API key: set ' + name + ' in .env or save one for ' + endpoint + ' in the app.')
    return key


def run(settings, paper, endpoint, model, reasoning, key, out, provider_name, compare, kind='overview'):
    settings = dict(settings, endpoint=endpoint, model=model, overview_reasoning=reasoning)
    usage = []
    current = {'stage': 'request', 'number': 0}

    def progress(message):
        # The coordinator announces "<stage> · request <n>" before each request.
        if message and ' · request ' in message:
            stage, _, number = message.partition(' · request ')
            current.update(stage=stage.strip(), number=int(number))
        elif message:
            print('  ' + message)

    def record(entry):
        usage.append(entry)
        print('  {stage}-request_{n}-in:{prompt:.3f}k-out:{completion:.3f}k'.format(
            stage=current['stage'], n=current['number'],
            prompt=entry.get('prompt_tokens', 0) / 1000, completion=entry.get('completion_tokens', 0) / 1000))

    provider = Provider(settings, key, on_usage=record)
    started = time.monotonic()
    result = (generate_blog if kind == 'blog' else generate_overview)(provider, paper, progress)
    seconds = round(time.monotonic() - started)
    tokens = sum(entry.get('total_tokens', 0) for entry in usage)
    reasoning_tokens = sum(entry.get('reasoning_tokens', 0) for entry in usage)
    stem = provider_name + '_' + _slug(paper.get('title', 'paper')[:60]) + ('_' + _slug(model) if compare else '')
    if kind == 'blog':
        summary = {'model': model, 'requests': len(usage), 'tokens': tokens, 'reasoning_tokens': reasoning_tokens,
                   'seconds': seconds, 'words': len(result['text'].split()),
                   'verdicts': result['provenance']['verdict_count'],
                   'figures': [{key: item[key] for key in ('id', 'status', 'requests', 'corrections')}
                               for item in result['provenance']['figure_outcomes']]}
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / (stem + '.md')).write_text(result['text'])
            for figure in result['figures']:
                target = out / (stem + '_' + figure['id'] + '.png')
                shutil.copyfile(Path(paper['directory']) / figure['png'], target)
                summary.setdefault('png', []).append(str(target))
        print(json.dumps(summary, indent=1))
        return
    figure = result['figures'][0]
    png = Path(paper['directory']) / figure['png']
    svg = Path(paper['directory']) / figure['svg_source']
    if out:
        out.mkdir(parents=True, exist_ok=True)
        # {provider}_{paper}.png; the model joins the name only when one invocation compares several.
        shutil.copyfile(png, out / (stem + '.png'))
        shutil.copyfile(svg, out / (stem + '.svg'))
        png, svg = out / (stem + '.png'), out / (stem + '.svg')
    print(json.dumps({'model': model, 'requests': len(usage), 'tokens': tokens,
                      'reasoning_tokens': reasoning_tokens, 'seconds': seconds,
                      'density': result['provenance']['checks']['density'],
                      'panels': result['provenance']['checks']['panels'],
                      'components': result['provenance']['checks']['components'],
                      'png': str(png), 'svg': str(svg)}, indent=1))


def _slug(text):
    return re.sub(r'[^A-Za-z0-9]+', '-', str(text)).strip('-').lower() or 'x'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--paper', required=True, help='part of the paper title, matched case-insensitively')
    parser.add_argument('--provider', choices=sorted(PROVIDERS), default='deepseek')
    parser.add_argument('--endpoint', help='base URL for --provider custom')
    parser.add_argument('--api_key', help='name of the .env or environment variable holding the key')
    parser.add_argument('--model', action='append', required=True, help='model id; repeat to compare')
    parser.add_argument('--reasoning', choices=('auto', *REASONING_EFFORTS), default='auto')
    parser.add_argument('--out', type=Path, help='directory that receives each run\'s PNG and SVG')
    parser.add_argument('--kind', choices=('overview', 'blog'), default='overview')
    parser.add_argument('--library', type=Path, default=LIBRARY,
                        help='library directory; defaults to the app library, '
                             'or an isolated one such as /tmp/localxiv-dev')
    arguments = parser.parse_args()
    endpoint, key_name = PROVIDERS[arguments.provider]
    if arguments.provider == 'custom':
        if not arguments.endpoint:
            parser.error('--provider custom needs --endpoint')
        endpoint = arguments.endpoint
    elif arguments.endpoint:
        parser.error('--endpoint applies to --provider custom only')
    settings, paper = load(arguments.paper, arguments.library)
    key = api_key(endpoint, arguments.api_key or key_name)
    for model in arguments.model:
        print('== ' + model + ' on ' + endpoint)
        try:
            run(settings, paper, endpoint, model, arguments.reasoning, key, arguments.out,
                arguments.provider, len(arguments.model) > 1, arguments.kind)
        except Exception as error:  # noqa: BLE001 - one model's failure must not stop the others
            print(json.dumps({'model': model, 'failed': str(error)[:400]}, indent=1))


if __name__ == '__main__':
    main()
