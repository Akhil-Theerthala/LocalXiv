"""The passage citations in generated text."""
import re

from papers.errors import ProviderError

# One bracketed group of passage IDs, such as [p00017] or [p00017, p00018].
CITATION = r'\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]'


def cited_in(items, text):
    """The passages of ``items`` that ``text`` cites, in citation order. An unknown ID, even one
    inside a grouped bracket, or no citation at all is a ``ProviderError``."""
    known = {item['id']: item for item in items}
    refs = [ref for group in re.findall(CITATION, text) for ref in re.findall(r'p\d+', group)]
    if any(ref not in known for ref in re.findall(r'\bp\d+\b', text)):
        raise ProviderError('Generated text cited an unknown passage. Retry generation.')
    if not refs:
        raise ProviderError('Generated text did not provide verifiable passage references; cite passages in '
                            'square brackets, such as [p00017]. Retry generation.')
    return [dict(known[ref]) for ref in dict.fromkeys(refs)]


def uncited(text):
    """``text`` without its passage citations, for a reader."""
    return re.sub(r'[ \t]*' + CITATION, '', text)
