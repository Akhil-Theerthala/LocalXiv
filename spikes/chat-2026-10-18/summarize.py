"""Summarize P3 runs: time to first words, tokens, cost, and citations, by phase.

  python summarize.py runs/anthropic.jsonl [runs/other.jsonl ...]

A question is warm when the provider read part of the prompt from its cache.
"""
import json
import statistics
import sys
from collections import defaultdict


def median(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 2) if values else None


def p90(values):
    values = sorted(v for v in values if v is not None)
    return round(values[min(len(values) - 1, int(0.9 * len(values)))], 2) if values else None


for path in sys.argv[1:]:
    rows = [json.loads(line) for line in open(path)]
    answers = [r for r in rows if 'text' in r]
    errors = [r for r in rows if 'error' in r]
    prewarms = [r for r in rows if r.get('phase') == 'prewarm' and 'usage' in r]
    print(f'== {path}: {len(answers)} answers, {len(errors)} errors, {len(prewarms)} pre-warms')
    for r in errors:
        print('  error', r.get('paper'), r.get('q'), r['error'][:160])
    groups = defaultdict(list)
    for r in answers:
        groups[r['phase'] + (' ' + r['ttl'] if r.get('ttl') else '')].append(r)
    print(f'  {"phase":<22}{"n":>3}{"first med":>10}{"first p90":>10}{"read>0":>8}{"input":>9}{"read":>9}'
          f'{"write":>9}{"output":>8}{"cost $":>10}')
    for name, group in sorted(groups.items()):
        usage = [r['usage'] for r in group]
        cost = [r['cost'] for r in group if r.get('cost') is not None]
        print(f'  {name:<22}{len(group):>3}{median(r["first_text"] for r in group)!s:>10}'
              f'{p90(r["first_text"] for r in group)!s:>10}{sum(u["cache_read"] > 0 for u in usage):>8}'
              f'{median(u["input"] for u in usage)!s:>9}{median(u["cache_read"] for u in usage)!s:>9}'
              f'{median(u["cache_write"] for u in usage)!s:>9}{median(u["output"] for u in usage)!s:>8}'
              f'{(round(statistics.mean(cost), 5) if cost else "-")!s:>10}')
    warm = [r for r in answers if r['usage']['cache_read'] > 0]
    cold = [r for r in answers if r['usage']['cache_read'] == 0]
    after_pause = [r for r in answers if (r.get('gap') or 0) > 300]
    print(f'  warm: n={len(warm)} first median={median(r["first_text"] for r in warm)} '
          f'p90={p90(r["first_text"] for r in warm)}; cold: n={len(cold)} '
          f'first median={median(r["first_text"] for r in cold)}')
    warm_after = sum(r['usage']['cache_read'] > 0 for r in after_pause)
    print(f'  after a pause over 300 s: n={len(after_pause)}, warm {warm_after}, '
          f'first median={median(r["first_text"] for r in after_pause)}')
    print(f'  first thinking median={median(r["first_thinking"] for r in answers)}, '
          f'total seconds median={median(r["seconds"] for r in answers)}')
    for r in prewarms:
        print(f'  prewarm {r["paper"]}: {r["seconds"]} s, write={r["usage"]["cache_write"]} '
              f'read={r["usage"]["cache_read"]} cost={r.get("cost")}')
    cited = sum(len(r['citations']['cited']) for r in answers)
    unknown = sum(len(r['citations']['unknown']) for r in answers)
    no_cite = sum(not r['citations']['cited'] for r in answers)
    loose = sum(r['citations']['outside_brackets'] > 0 for r in answers)
    print(f'  citations: {cited} IDs, {unknown} unknown, {cited - unknown} known '
          f'({(cited - unknown) / cited:.1%} known); answers with no citation: {no_cite}; '
          f'answers with an ID outside brackets: {loose}' if cited else '  citations: none')
    total = sum(r.get('cost') or 0 for r in rows)
    print(f'  total cost ${total:.4f}' if total else '  total cost: not priced')
