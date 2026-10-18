"""The passage citations in generated text."""
import re

from papers.errors import ProviderError

# One bracketed group of passage IDs, such as [p00017] or [p00017, p00018].
CITATION = r'\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]'


def chat_citations(items, text):
    """The passages of ``items`` that ``text`` cites inside brackets, in citation order, and the cited IDs that
    no passage has. Never raises. An ordinary word such as "p50" outside brackets is not a citation."""
    known = {item['id']: item for item in items}
    refs = dict.fromkeys(ref for group in re.findall(CITATION, text) for ref in re.findall(r'p\d+', group))
    return [dict(known[ref]) for ref in refs if ref in known], [ref for ref in refs if ref not in known]


def cited_in(items, text):
    """The passages of ``items`` that ``text`` cites, in citation order. An unknown ID, even one
    inside a grouped bracket, or no citation at all is a ``ProviderError``."""
    cites, unknown = chat_citations(items, text)
    if unknown:
        raise ProviderError('Generated text cited an unknown passage. Retry generation.')
    if not cites:
        raise ProviderError('Generated text did not provide verifiable passage references; cite passages in '
                            'square brackets, such as [p00017]. Retry generation.')
    return cites


def uncited(text):
    """``text`` without its passage citations, for a reader."""
    return re.sub(r'[ \t]*' + CITATION, '', text)
