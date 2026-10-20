"""The Notes of Papers as Markdown, in the order that All Notes shows them (app/static/notes.js)."""
import math
import re

from papers.chat import COLOURS
from papers.passages import uncited


def notes_markdown(items):
    """One Markdown text for the (Paper, records, Note groups) items: per Paper the title and the arXiv link, then
    per record its section, quote, localxiv:// link, colour name, the Not found line, its Note, and each question with
    its answer.
    When the Paper has groups, each group with records gets a `##` heading, and the sections go one level down."""
    blocks = []
    for paper, records, groups in items:
        sections = {passage['id']: passage.get('section') for passage in paper.get('passages') or []}
        blocks += [f'# {paper.get("title") or paper["id"]}',
                   '<https://arxiv.org/abs/' + re.sub(r'v\d+$', '', paper.get('arxiv_id') or paper['id']) + '>']
        level = '###' if groups else '##'
        for group, part in arranged(paper, records, groups):
            if group:
                blocks.append(f'## {group}')
            for record in part:
                paper_note = _paper_note(record)
                other = 'Question about the Paper' if record['whole'] else 'Paper note' if paper_note else 'No section'
                blocks.append(f'{level} ' + (sections.get(record['passage']) or record['section'] or other))
                if record['quote']:
                    blocks.append('\n'.join('> ' + line for line in record['quote'].split('\n')))
                # The Mac app opens the Paper at the passage. A record outside a passage has no place to open.
                if record['passage']:
                    blocks.append(f'<localxiv://open?paper={paper["id"]}&passage={record["passage"]}>')
                blocks.append(f'*{COLOURS[record["colour"]]}*')
                # Only the page can search words outside a passage, so the export trusts `found`.
                if record['found'] == 'not-found':
                    blocks.append('Not found in this version')
                if record['note'].strip():
                    blocks.append(record['note'].strip())
                for turn in record['turns']:
                    blocks.append(f'**{turn["question"]}**')
                    if answer := uncited(turn['answer'].get('text') or '').strip():
                        blocks.append(answer)
    return '\n\n'.join(blocks) + '\n'


def _paper_note(record):
    return not record['quote'] and not record['passage']


def arranged(paper, records, groups):
    """The (group name, records) parts. In Groups order: each group with records in list order, then "In no group"
    when it has records. Inside a group, `order` comes first, and a record with no order comes after it in reading
    order. In Position order, one part with no name, and a Paper note comes first."""
    passages = paper.get('passages') or []
    where = {passage['id']: index for index, passage in enumerate(passages)}

    def key(record):
        index = where.get(record['passage'])
        start = -1 if index is None else 0 if record['whole'] else offset(
            passages[index].get('text') or '', record['match'] or record['head'] or record['quote'], record['prefix'],
            record['suffix'])
        place = (math.inf if index is None else index, math.inf if start < 0 else start)
        first = 0 if _paper_note(record) else 1
        if groups:
            return (math.inf if record['order'] is None else record['order'], first, *place, record['created_at'])
        return (first, *place, record['created_at'])

    records = sorted(records, key=key)
    if not groups:
        return [(None, records)]
    names = {}
    for group in groups:
        names.setdefault(group['id'], group['name'])
    parts = [(name, [record for record in records if record['group'] == group]) for group, name in names.items()]
    parts.append(('In no group', [record for record in records if record['group'] not in names]))
    return [(name, part) for name, part in parts if part]


def offset(text, quote, prefix, suffix):
    """The place of quote in text whose surroundings agree with the most characters of prefix (read backwards) and
    suffix, or the first place when they agree equally, as findOffset in app/static/onetext.js. -1 when not found."""
    best, most = -1, -1
    at = text.find(quote) if quote else -1
    while at >= 0:
        before = after = 0
        stop = at + len(quote)
        while before < len(prefix) and before < at and text[at - 1 - before] == prefix[-1 - before]:
            before += 1
        while after < len(suffix) and stop + after < len(text) and text[stop + after] == suffix[after]:
            after += 1
        if before + after > most:
            best, most = at, before + after
        at = text.find(quote, at + 1)
    return best
