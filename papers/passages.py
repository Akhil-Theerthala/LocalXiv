"""The retained passages a request carries, and the passage citations in generated text."""
import re

from papers.errors import ProviderError


class Passages:
    """Passages as evidence for one request: the text a prompt carries and the citations it allows."""

    # One bracketed group of passage IDs, such as [p00017] or [p00017, p00018].
    CITATION = r'\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]'

    def __init__(self, items):
        self.items = list(items)

    def prompt_text(self):
        """Each passage under its ID and section, as the prompts carry evidence."""
        return '\n\n'.join('[' + item['id'] + '] ' + item.get('section', '') + '\n' + item['text'] for item in self.items)

    def cited_in(self, text):
        """The passages ``text`` cites, in citation order. An unknown ID, even one inside a grouped
        bracket, or no citation at all is a ``ProviderError``."""
        known = {item['id']: item for item in self.items}
        refs = [ref for group in re.findall(self.CITATION, text) for ref in re.findall(r'p\d+', group)]
        if any(ref not in known for ref in re.findall(r'\bp\d+\b', text)):
            raise ProviderError('Generated text cited an unknown passage. Retry generation.')
        if not refs:
            raise ProviderError('Generated text did not provide verifiable passage references; cite passages in '
                                'square brackets, such as [p00017]. Retry generation.')
        return [dict(known[ref]) for ref in dict.fromkeys(refs)]

    @classmethod
    def uncited(cls, text):
        """``text`` without its passage citations, for a reader."""
        return re.sub(r'[ \t]*' + cls.CITATION, '', text)
