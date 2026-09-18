"""Generate an Overview for one library paper with any endpoint and model, without saving it.

Usage, from the repository root with the renderer built:

    .venv/bin/python tools/overview_run.py --paper "Attention" --model deepseek-flash
    .venv/bin/python tools/overview_run.py --paper "Attention" --endpoint https://api.openai.com/v1 --model gpt-5
    .venv/bin/python tools/overview_run.py --paper "Probabilities" --model deepseek-flash --reasoning off

The API key comes from the Keychain entry the app saved for that endpoint, or from
LOCALXIV_API_KEY. The run writes only under the paper's reader/overview-figures/ directory and
prints the request count, tokens, seconds, density, and the PNG path. It never touches the saved
Overview. Pass --model several times to compare models on one endpoint.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papers.ai import Provider  # noqa: E402
from papers.overview_workflow import generate  # noqa: E402
from papers.settings import get_key  # noqa: E402

LIBRARY = Path.home() / 'Library/Application Support/LocalXiv/library'


def load(paper_title):
    db = sqlite3.connect(LIBRARY / 'library.sqlite3')
    try:
        settings = json.loads(db.execute('select value from settings').fetchone()[0])
        papers = [json.loads(row[0]) for row in db.execute('select value from papers')]
    finally:
        db.close()
    matches = [paper for paper in papers if paper_title.lower() in paper.get('title', '').lower()]
    if len(matches) != 1:
        raise SystemExit('Paper filter matched ' + str(len(matches)) + ' papers: '
                         + ', '.join(paper.get('title', '')[:50] for paper in matches))
    return settings, matches[0]


def run(settings, paper, endpoint, model, reasoning):
    settings = dict(settings, endpoint=endpoint, model=model, overview_reasoning=reasoning)
    key = os.environ.get('LOCALXIV_API_KEY') or get_key(endpoint)
    if not key:
        raise SystemExit('No API key for ' + endpoint + '. Save one in the app or set LOCALXIV_API_KEY.')
    usage = []
    provider = Provider(settings, key, on_usage=usage.append)
    started = time.monotonic()
    result = generate(provider, paper, lambda message: print('  ' + message) if message else None)
    seconds = round(time.monotonic() - started)
    figure = result['figures'][0]
    tokens = sum(entry.get('total_tokens', 0) for entry in usage)
    reasoning_tokens = sum(entry.get('reasoning_tokens', 0) for entry in usage)
    print(json.dumps({'model': model, 'requests': len(usage), 'tokens': tokens,
                      'reasoning_tokens': reasoning_tokens, 'seconds': seconds,
                      'density': result['provenance']['checks']['density'],
                      'panels': result['provenance']['checks']['panels'],
                      'components': result['provenance']['checks']['components'],
                      'png': str(Path(paper['directory']) / figure['png'])}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--paper', required=True, help='part of the paper title, matched case-insensitively')
    parser.add_argument('--endpoint', help='provider base URL; default is the saved setting')
    parser.add_argument('--model', action='append', required=True, help='model id; repeat to compare')
    parser.add_argument('--reasoning', choices=('low', 'off'), default='low')
    arguments = parser.parse_args()
    settings, paper = load(arguments.paper)
    endpoint = arguments.endpoint or settings['endpoint']
    for model in arguments.model:
        print('== ' + model + ' on ' + endpoint)
        try:
            run(settings, paper, endpoint, model, arguments.reasoning == 'low')
        except Exception as error:  # noqa: BLE001 - one model's failure must not stop the others
            print(json.dumps({'model': model, 'failed': str(error)[:400]}, indent=1))


if __name__ == '__main__':
    main()
