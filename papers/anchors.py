"""Find the words of a Highlight again in a new version of its Paper.

Passage IDs and DOM anchors are positions, so after a reimport they can name other text: they are hints only.
docs/verification/2026-10-19-anchor-spike.md has the measures behind each step and the threshold.
"""
import math
import re
import unicodedata
from difflib import SequenceMatcher

THRESHOLD = 0.85  # 0 of 1,850 quotes of an unrelated Paper matched at 0.85; 3 matched at 0.8
CANDIDATES = 10  # fuzzy candidates by word rarity, in addition to the passages with the old href and ID
LETTERS = 15  # the shortest letters-and-digits form that the spike measured with no false match
WORD = re.compile(r'[^\W_]{3,}')
NOT_LETTER = re.compile(r'[\W_]+')
POSITION = re.compile(r'p(\d+)')


def locate(passages, record):
    """The record's new {passage, href, section, found, match, end}, or None when the search fails. It never raises.

    A record with no passage or no quote is not searched: its fields come back as they are.
    A part that the search cannot find makes the record not-found, with its old passage, href, and section.
    """
    kept = {key: record.get(key) for key in ('passage', 'href', 'section', 'found', 'match', 'end')}
    if not (record.get('passage') and record.get('quote')):
        return kept
    try:
        paper, end = _paper(passages), record.get('end')
        if not end:
            found = _find(paper, record['passage'], record['href'], record['section'], record['quote'],
                          record['prefix'], record['suffix'])
            if not found:
                return dict(kept, found='not-found', match=None)
            index, words = found
            return dict(_place(paper, index), end=None, found='moved' if words else 'found', match=words)
        # A selection across passages: the head ends its passage, and the end part starts a later one.
        start = _find(paper, record['passage'], record['href'], record['section'], record['head'], record['prefix'], '')
        last = _find(paper, end['passage'] or record['passage'], end['href'], record['section'], end['quote'], '',
                     end['suffix'])
        if not (start and last and last[0] > start[0]):
            return dict(kept, found='not-found', match=None)
        (index, head), (stop, tail) = start, last
        return dict(_place(paper, index), end=dict(end, passage=paper.ids[stop], href=paper.hrefs[stop]),
                    found='moved' if head or tail else 'found',
                    match=f"{head or record['head']} {tail or end['quote']}" if head or tail else None)
    except Exception:
        return None


class _Paper:
    def __init__(self, passages):
        self.texts = [passage.get('text') or '' for passage in passages]
        self.ids = [passage.get('id') for passage in passages]
        self.hrefs = [passage.get('href') for passage in passages]
        self.sections = [passage.get('section') for passage in passages]
        self.by_id, self.by_href = {}, {}
        for index, passage in enumerate(passages):
            self.by_id.setdefault(passage.get('id'), index)
            self.by_href.setdefault(passage.get('href'), index)
        self._letters = self._words = None

    def letters(self):
        if self._letters is None:
            self._letters = [_letters(text) for text in self.texts]
        return self._letters

    def words(self):
        """The words of each passage, and for each word the passages that hold it."""
        if self._words is None:
            words = [set(WORD.findall(_fold(text))) for text in self.texts]
            holders = {}
            for index, found in enumerate(words):
                for word in found:
                    holders.setdefault(word, set()).add(index)
            self._words = words, holders
        return self._words


# One Paper: the caller searches every record of a Paper with the same list, so the indexes are built once.
# The tuple keeps the list alive, so its id cannot name another list.
_last = (None, None)


def _paper(passages):
    global _last
    cached = _last
    if cached[0] is not passages:
        cached = _last = (passages, _Paper(passages))
    return cached[1]


def _place(paper, index):
    return dict(passage=paper.ids[index], href=paper.hrefs[index], section=paper.sections[index])


def _fold(text):
    return unicodedata.normalize('NFKC', text).casefold()


def _letters(text):
    return NOT_LETTER.sub('', _fold(text))


def _find(paper, passage, href, section, quote, prefix, suffix):
    """(passage index, new words) of one part, with new words None for an exact match, or None when not found."""
    if not quote:
        return None
    number = POSITION.fullmatch(passage or '')
    old = int(number[1]) - 1 if number else paper.by_href.get(href, 0)

    def near(index):
        return abs(index - old)

    full = len(prefix) + len(suffix)
    for index in (paper.by_href.get(href), paper.by_id.get(passage)):
        if index is not None and _context(paper.texts[index], quote, prefix, suffix) == full:
            return index, None
    in_section = [index for index, name in enumerate(paper.sections) if section is not None and name == section]
    for indexes in (in_section, range(len(paper.texts))):
        hits = [(-agree, near(index), index) for index in indexes
                if (agree := _context(paper.texts[index], quote, prefix, suffix)) >= 0]
        if hits:
            return min(hits)[2], None
    form = _letters(quote)
    if len(form) >= LETTERS:
        forms = paper.letters()
        for index in sorted((index for index, letters in enumerate(forms) if form in letters),
                            key=lambda index: (paper.sections[index] != section, near(index))):
            words = _same_letters(paper.texts[index], form)
            if words:
                return index, words
    best = {}
    matcher = SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(quote)
    for index in _candidates(paper, quote, href, passage, near):
        ratio, start, stop = _window(matcher, quote, paper.texts[index])
        for scope in ('paper', 'section') if paper.sections[index] == section else ('paper',):
            if ratio >= THRESHOLD and ratio > best.get(scope, (0,))[0]:
                best[scope] = ratio, index, paper.texts[index][start:stop]
    if best:
        _, index, words = best.get('section') or best['paper']
        return index, words
    return None


def _context(text, quote, prefix, suffix):
    """The most characters of prefix (read backwards) and suffix that agree around a place of quote, or -1."""
    best, at = -1, text.find(quote)
    while at >= 0:
        before, after, stop = 0, 0, at + len(quote)
        while before < len(prefix) and before < at and text[at - 1 - before] == prefix[-1 - before]:
            before += 1
        while after < len(suffix) and stop + after < len(text) and text[stop + after] == suffix[after]:
            after += 1
        best, at = max(best, before + after), text.find(quote, at + 1)
    return best


def _same_letters(text, form):
    """The whole words of text whose letters and digits are form, or None."""
    letters, places = [], []
    for at, char in enumerate(text):
        for letter in _letters(char):
            letters.append(letter)
            places.append(at)
    start = ''.join(letters).find(form)
    if start < 0:
        return None
    return text[_word_start(text, places[start]):_word_stop(text, places[start + len(form) - 1] + 1)]


def _candidates(paper, quote, href, passage, near):
    """The passages with the old href and ID, and the 10 with the most IDF overlap among those that hold one of the
    quote's 3 rarest words. Plain difflib on every passage took 30.5 s for 50 quotes in the spike."""
    words, holders = paper.words()
    present = sorted((len(holders[word]), word) for word in set(WORD.findall(_fold(quote))) if word in holders)
    pool = set().union(*(holders[word] for _, word in present[:3]))
    weight = {word: math.log(1 + len(paper.texts) / count) for count, word in present}
    ranked = sorted(pool, key=lambda index: (-sum(w for word, w in weight.items() if word in words[index]),
                                             near(index)))
    hints = {paper.by_href.get(href), paper.by_id.get(passage)} - {None}
    return sorted(set(ranked[:CANDIDATES]) | hints)


def _word_start(text, at):
    while at > 0 and text[at - 1] != ' ':
        at -= 1
    return at


def _word_stop(text, at):
    while at < len(text) and text[at] != ' ':
        at += 1
    return at


def _window(matcher, quote, text):
    """The best ratio of the quote against one window of text: (ratio, start, stop). The window is put at the longest
    common substring (and at a second one in the larger unmatched part of the quote), then trimmed."""
    length, size = len(quote), len(text)
    if not size:
        return 0.0, 0, 0
    if size <= length * 1.3:
        return _trimmed(matcher, text, 0, size)
    matcher.set_seq1(text)
    first = matcher.find_longest_match(0, size, 0, length)
    if not first.size:
        return 0.0, 0, 0
    shifts = [first.a - first.b]
    low, high = max((0, first.b), (first.b + first.size, length), key=lambda part: part[1] - part[0])
    if high - low >= 8:
        second = matcher.find_longest_match(0, size, low, high)
        if second.size >= 4 and abs(second.a - second.b - shifts[0]) > length // 4:
            shifts.append(second.a - second.b)
    slack, best = length // 4 + 8, (0.0, 0, 0)
    for shift in shifts:
        start, stop = _word_start(text, max(0, shift - slack)), _word_stop(text, min(size, shift + length + slack))
        if stop > start:
            best = max(best, _trimmed(matcher, text, start, stop))
    return best


def _trimmed(matcher, text, start, stop):
    """The ratio of the quote against text[start:stop], or against that window trimmed to its first and last
    matching blocks of 3 or more characters when that is higher."""
    matcher.set_seq1(text[start:stop])
    ratio = matcher.ratio()
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= 3]
    if blocks:
        low = _word_start(text, start + blocks[0].a)
        high = _word_stop(text, start + blocks[-1].a + blocks[-1].size)
        if (low, high) != (start, stop) and high > low:
            matcher.set_seq1(text[low:high])
            trimmed = matcher.ratio()
            if trimmed > ratio:
                return trimmed, low, high
    return ratio, start, stop
