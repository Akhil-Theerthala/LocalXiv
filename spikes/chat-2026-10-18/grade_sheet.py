"""Write a grading sheet: each sampled answer beside the text of every passage it cites.

  python grade_sheet.py OUT.md RUN.jsonl:Q,Q [RUN.jsonl:Q,Q ...]

Each argument names a run file and the question indices to sample from every Paper in it.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from chat_spike import load_paper  # noqa: E402

out = ['# Grading sheet\n\nGrade each claim: does the cited passage support it? (yes, partly, no)\n']
views = {}
for spec in sys.argv[2:]:
    path, indices = spec.split(':')
    wanted = {int(i) for i in indices.split(',')}
    for row in map(json.loads, open(path)):
        if 'text' not in row or row['q'] not in wanted:
            continue
        if row['paper'] not in views:
            views[row['paper']] = {p['id']: p for p in load_paper(row['paper'])[1]['passages']}
        passages = views[row['paper']]
        out.append(f'\n## {Path(path).stem} · {row["paper"]} · q{row["q"]} · {row["phase"]}\n')
        selection = f' (selection {row["selection"]})' if row.get('selection') else ''
        out.append(f'**Question:** {row["question"]}{selection}')
        out.append(f'\n**Answer:**\n\n{row["text"]}\n')
        for ref in dict.fromkeys(row['citations']['cited']):
            text = ' '.join(passages[ref]['text'].split()) if ref in passages else '(unknown ID)'
            out.append(f'- `{ref}`: {text[:1500]}')
Path(sys.argv[1]).write_text('\n'.join(out) + '\n')
print(sys.argv[1], sum(line.startswith('\n## ') for line in out), 'answers')
