"""Find Paper: the arXiv Paper of a bibliography entry, from the title in the entry."""
import re
import unicodedata

from papers import search

# A period ends a sentence after two characters that are not a dot or a space, so an initial such as "N." does not.
SENTENCE = re.compile(r'(?<=[^\s.]{2})\.\s+')


def fingerprint(text):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKC', text).lower())


def reference_title(text):
    """Return the title of an entry: quoted, after a (year), the second sentence, or else the whole entry."""
    entry = re.sub(r'^\s*\[\d+\]\s*', '', text)
    entry = re.sub(r'(?:\bURL:?\s+)?\S*(?:https?://|(?:ar|alpha)xiv\.org/)\S*', ' ', entry, flags=re.I)
    entry = ' '.join(entry.split())
    for quoted in re.findall(r'[“"]([^”"]+)[”"]', entry):
        if len(quoted.split()) >= 2:
            return quoted.strip().rstrip(',')[:300]
    for year in re.finditer(r'\(\d{4}[a-z]?\)', entry):
        sentence = SENTENCE.split(entry[year.end():].lstrip(' .,:'))[0].strip()
        if len(sentence.split()) >= 2 and sentence.count(',') < 3:
            return sentence[:300]
    sentences = SENTENCE.split(entry)
    return (sentences[1] if len(sentences) > 1 and len(sentences[1].split()) >= 3 else entry)[:300]


def resolve_reference(text, pwc=False):
    """Return {'arxiv_id', 'title'} for a match that the guard accepts, else {'query'} for Paper search.

    With `pwc`, Papers with Code keyword search goes first, and the S2 title match only when it finds nothing."""
    title = reference_title(text)
    entry, extracted = fingerprint(text), fingerprint(title)

    def accepted(rows):
        # A short, generic title such as "Language Models" can be inside the entry, so the match must be most
        # of the extracted title.
        for row in rows or []:
            found = fingerprint(row['title'])
            if len(found) >= 12 and found in entry and len(found) >= 0.8 * len(extracted):
                return {'arxiv_id': row['arxiv_id'], 'title': row['title']}

    if pwc and (row := accepted(search.lookup('paperswithcode', title, 3, None))):
        return row
    try:
        key = search.get_key(search.S2)
    except RuntimeError:
        key = ''
    return accepted(search.lookup('semantic_scholar_match', title, 1, None, key)) or {'query': title}
