"""The Highlights and Notes of a Paper inside its packaged EPUB: a mark on the words of each Highlight, with a number
that links to a Highlights and Notes chapter at the end of the book."""
import html
import posixpath
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from native.host import validate_epub
from papers.chat import COLOURS
from papers.document import MATH, XHTML, _tex, epubcheck, local, xml_bytes
from papers.notes_export import arranged, offset
from papers.passages import uncited

CHAPTER = 'EPUB/notes.xhtml'
STYLES = ('mark.lx-key{background:#fff3b0} mark.lx-question{background:#e9d8ff} mark.lx-use{background:#ffe0c2}\n'
          'mark.lx-disagree{background:#ffd6e0} mark[class^=lx-]{text-decoration:underline}\n'
          'a.lx-ref{font-size:0.7em;vertical-align:super;text-decoration:none}\n')


def notes_epub(source: Path, paper: dict, records: list[dict], groups: list[dict], output: Path) -> Path:
    """Write `output`: `source` with the words of each found record marked in its colour, and the chapter added.
    `source` is not changed. Raises ValueError with the EPUBCheck line when the result is not a valid book."""
    parts = arranged(paper, records, groups)
    numbers = {record['id']: k for k, record in enumerate((record for _, part in parts for record in part), 1)}
    stored = {passage['id']: passage for passage in paper.get('passages') or []}
    with zipfile.ZipFile(source) as book:
        files = {info.filename: book.read(info.filename) for info in book.infolist()}
    trees = {}
    for record in sorted(records, key=lambda record: numbers[record['id']]):
        if record['found'] == 'not-found' or not record['passage'] or not record['quote'] or not record['href']:
            continue
        name = _file(record['href'])
        if name not in files:
            continue
        if name not in trees:
            trees[name] = ET.fromstring(files[name])
        _mark(trees[name], record, stored, numbers[record['id']], posixpath.relpath(CHAPTER, posixpath.dirname(name)))
    for name, tree in trees.items():
        files[name] = xml_bytes(tree)
    files['EPUB/reading.css'] = files.get('EPUB/reading.css', b'') + STYLES.encode()
    files['EPUB/content.opf'] = files['EPUB/content.opf'].decode().replace(
        '</manifest>', '<item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/></manifest>').replace(
        '</spine>', '<itemref idref="notes"/></spine>').encode()
    nav = files['EPUB/nav.xhtml'].decode()
    at = nav.rindex('</ol>')
    files['EPUB/nav.xhtml'] = (nav[:at] + '<li><a href="notes.xhtml">Highlights and Notes</a></li>' + nav[at:]).encode()
    files[CHAPTER] = _chapter(parts, numbers, stored).encode()
    candidate = output.with_name('.' + output.name)
    try:
        with zipfile.ZipFile(candidate, 'w') as book:
            for name, data in files.items():
                book.writestr(name, data,
                              compress_type=zipfile.ZIP_STORED if name == 'mimetype' else zipfile.ZIP_DEFLATED)
        validate_epub(candidate)
        epubcheck(candidate, output.with_suffix('.epubcheck.log'))
        candidate.replace(output)
    finally:
        candidate.unlink(missing_ok=True)
    return output


def _file(href):
    """The book member of a record's href, which the reader reads under the Paper's reader directory."""
    return 'EPUB/' + href.split('#')[0].removeprefix('reader/')


def _mark(tree, record, stored, number, chapter_href):
    """Wrap the words of the record in `tree` in marks, one per text run, and put the number link after the last."""
    ids = {element.get('id'): element for element in tree.iter() if element.get('id')}
    parents = {child: parent for parent in tree.iter() for child in parent}
    first, end = ids.get(record['href'].split('#')[-1]), record['end']
    if first is None:
        return
    text, sources = _map(first, (stored.get(record['passage']) or {}).get('text') or '')
    if not end:
        quote = record['match'] or record['quote']
        start = offset(text, quote, record['prefix'], record['suffix'])
        if start < 0:
            return
        segments = _segments(sources, start, start + len(quote))
    else:
        # A selection across passages: its words at the end of the first passage, everything between, and its words at
        # the start of the last passage, as the Paper view paints it.
        last = ids.get((end['href'] or '').split('#')[-1])
        if last is None:
            return
        start = offset(text, record['head'] or '', record['prefix'], '')
        tail_text, tail_sources = _map(last, (stored.get(end['passage']) or {}).get('text') or '')
        stop = offset(tail_text, end['quote'], '', end['suffix'])
        if start < 0 or stop < 0:
            return
        segments = (_segments(sources, start, len(text)) + _between(tree, parents, first, last)
                    + _segments(tail_sources, 0, stop + len(end['quote'])))
    marks = [_wrap(parents, segment, 'lx-' + record['colour']) for segment in reversed(segments)]
    holder = next((mark for mark in marks if mark is not None), None)
    if holder is None:
        return
    # A link inside a link is not XHTML, so the number goes after the link that holds the last words.
    element = holder
    while element in parents:
        element = parents[element]
        if local(element.tag) == 'a':
            holder = element
    ref = ET.Element(f'{{{XHTML}}}a', {'class': 'lx-ref', 'href': f'{chapter_href}#n{number}'})
    ref.text, ref.tail, holder.tail = f'[{number}]', holder.tail, None
    parent = parents[holder]
    parent.insert(list(parent).index(holder) + 1, ref)


def _map(root, stored_text):
    """The one text of `root` as papers/document.py _text builds it (app/static/onetext.js textMap in the browser),
    and the source of each character: (element, 'text' or 'tail', offset in that string), or (formula, None, None).
    A formula image's alt is its TeX when the stored passage text has a formula there, else its plain text."""
    chars, sources, pending = [], [], None

    def add(char, source):
        nonlocal pending
        if char.isspace():
            if pending is None:
                pending = source
            return
        if pending is not None and chars:
            chars.append(' ')
            sources.append(pending)
        pending = None
        chars.append(char)
        sources.append(source)

    def walk(element):
        for at, char in enumerate(element.text or ''):
            add(char, (element, 'text', at))
        for child in element:
            value = None
            if _ref(child):
                pass  # The number link of an earlier mark is not text of the Paper.
            elif local(child.tag) == 'math':
                tex = _tex(child)
                value = f'${tex}$' if tex else ''.join(child.itertext())
            elif local(child.tag) == 'img' and 'math-image' in (child.get('class') or '').split():
                alt = child.get('alt') or ''
                value = f'${alt}$' if stored_text[len(chars):].lstrip().startswith('$') else alt
            else:
                walk(child)
            if value is not None:
                for char in f' {value} ':
                    add(char, (child, None, None))
            for at, char in enumerate(child.tail or ''):
                add(char, (child, 'tail', at))

    walk(root)
    return ''.join(chars), sources


def _ref(element):
    return local(element.tag) == 'a' and 'lx-ref' in (element.get('class') or '').split()


def _segments(sources, start, stop):
    """[element, kind, first offset, last offset + 1] of each run of characters from one string in
    sources[start:stop]. The characters of a formula make no segment."""
    segments = []
    for element, kind, at in sources[start:stop]:
        if kind is None:
            continue
        if segments and segments[-1][0] is element and segments[-1][1] == kind:
            segments[-1][3] = at + 1
        else:
            segments.append([element, kind, at, at + 1])
    return segments


def _between(tree, parents, first, last):
    """The whole strings between the end of `first` and the start of `last`: the tail of `first`, then the text of
    each element between them and the tail of each one that does not hold `last`."""
    holders, element = set(), last
    while element in parents:
        element = parents[element]
        holders.add(element)
    order = list(tree.iter())
    segments, inside = [[first, 'tail', 0, len(first.tail or '')]], set()
    for element in order[order.index(first) + len(list(first.iter())):order.index(last)]:
        # A formula gets no mark inside it, and the number link of an earlier mark is not text of the Paper.
        if element in inside:
            continue
        if element.tag.startswith(f'{{{MATH}}}') or _ref(element):
            inside.update(element.iter())
        else:
            segments.append([element, 'text', 0, len(element.text or '')])
        if element not in holders:
            segments.append([element, 'tail', 0, len(element.tail or '')])
    return segments


def _wrap(parents, segment, colour):
    """Move segment's characters into a new mark element, or return None when they are blank."""
    element, kind, start, stop = segment
    value = (element.text if kind == 'text' else element.tail) or ''
    if not value[start:stop].strip():
        return None
    mark = ET.Element(f'{{{XHTML}}}mark', {'class': colour})
    mark.text, mark.tail = value[start:stop], value[stop:]
    if kind == 'text':
        element.text = value[:start]
        element.insert(0, mark)
        parents[mark] = element
    else:
        element.tail = value[:start]
        parent = parents[element]
        parent.insert(list(parent).index(element) + 1, mark)
        parents[mark] = parent
    return mark


def _chapter(parts, numbers, stored):
    """The Highlights and Notes chapter, in the order of the Markdown export, with the entry n<k> for each record."""
    body = ['<h1>Highlights and Notes</h1>']
    level = 'h3' if any(name for name, _ in parts) else 'h2'
    for name, part in parts:
        if name:
            body.append(f'<h2>{html.escape(name)}</h2>')
        for record in part:
            paper_note = not record['quote'] and not record['passage']
            other = 'Question about the Paper' if record['whole'] else 'Paper note' if paper_note else 'No section'
            section = (stored.get(record['passage']) or {}).get('section') or record['section'] or other
            body.append(f'<section id="n{numbers[record["id"]]}"><{level}>{html.escape(section)}</{level}>')
            if record['quote']:
                quote = html.escape(record['quote']).replace('\n', '<br/>')
                # A Not found record keeps its old passage, where its words are gone, so it gets no link.
                if record['passage'] and record['href'] and record['found'] != 'not-found':
                    href = html.escape(record['href'].removeprefix('reader/'), quote=True)
                    quote = f'<a href="{href}">{quote}</a>'
                body.append(f'<blockquote>{quote}</blockquote>')
            body.append(f'<p><em>{COLOURS[record["colour"]]}</em></p>')
            if record['found'] == 'not-found':
                body.append('<p>Not found in this version</p>')
            if record['note'].strip():
                body.append(_paragraph(record['note']))
            for turn in record['turns']:
                body.append(f'<p><strong>{html.escape(turn["question"])}</strong></p>')
                if answer := uncited(turn['answer'].get('text') or '').strip():
                    body.append(_paragraph(answer))
            body.append('</section>')
    return (f'<html xmlns="{XHTML}"><head><title>Highlights and Notes</title>'
            '<link rel="stylesheet" type="text/css" href="reading.css"/></head><body>' + ''.join(body)
            + '</body></html>')


def _paragraph(text):
    return '<p>' + html.escape(text.strip()).replace('\n', '<br/>') + '</p>'
