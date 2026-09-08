import unittest
from sample_listings import parse


class SamplingTests(unittest.TestCase):
    def test_listing_keeps_identity_title_notes_and_journal_evidence(self):
        page='''<dt><a href ="/abs/2401.00022">arXiv:2401.00022</a></dt>
<dd><div class='meta'><div class='list-title mathjax'><span class='descriptor'>Title:</span>
Lecture notes on $x &lt; y$</div><div class='list-authors'><a>A. Author</a></div>
<div class='list-comments mathjax'><span>Comments:</span> 102 pages; lecture notes</div>
<div class='list-journal-ref'><span>Journal-ref:</span> Journal 3 (2024)</div>
<div class='list-subjects'><span>Subjects:</span> Algebra (math.AC)</div></div></dd>'''
        records=parse(page,'snapshot.html')
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['id'],'2401.00022')
        self.assertEqual(records[0]['title'],'Lecture notes on $x < y$')
        self.assertEqual(records[0]['comment'],'102 pages; lecture notes')
        self.assertEqual(records[0]['journal_ref'],'Journal 3 (2024)')
        self.assertEqual(records[0]['listing'],'snapshot.html')


if __name__=='__main__':unittest.main()
