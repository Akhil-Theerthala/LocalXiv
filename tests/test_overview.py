import unittest
from papers.overview import clean_citations
from papers.ai import _sources, ProviderError


class OverviewTests(unittest.TestCase):
    def test_grouped_citations_disappear_but_evidence_is_retained(self):
        value = 'Result [p00001, p00007; p00053]. Keep [2025], x[0], and 91.3% [p00001].'
        self.assertEqual('Result. Keep [2025], x[0], and 91.3%.', clean_citations(value))
        self.assertEqual('    keep  spacing\n', clean_citations('    keep  spacing [p00001]\n'))
        refs = _sources(value, [{'id': p} for p in ('p00001','p00007','p00053')])
        self.assertEqual(['p00001','p00007','p00053'], [r['id'] for r in refs])
        with self.assertRaises(ProviderError):
            _sources('[p00001, p99999]', [{'id':'p00001'}])
