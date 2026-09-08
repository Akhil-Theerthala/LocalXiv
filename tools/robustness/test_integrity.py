"""These tests damage output deliberately; they test the checks, not the parser."""
import unittest
from integrity import compare, snapshot

SOURCE='''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1 id="method">Method</h1><p>The first paragraph contains the main claim.</p>
<p>The second paragraph states a necessary limitation.</p>
<table><tr><th>Method</th><th>Score</th></tr><tr><td>A</td><td>−0.25 ✓</td></tr>
<tr><td>B</td><td>0.50 †</td></tr></table>
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mi>x</mi><mo>−</mo><mn>1</mn></mrow></math>
<figure><img src="plot.png" alt="Measured outcomes"/><figcaption>Result plot</figcaption></figure>
<a href="#method">Method</a></body></html>'''


def read(s):return snapshot({'main.xhtml':s.encode()},{'plot.png':b'known image pixels'})


class IntegrityTests(unittest.TestCase):
    def test_detects_each_deliberate_content_corruption(self):
        baseline=read(SOURCE)
        cases=[('prose',SOURCE.replace('<p>The second paragraph states a necessary limitation.</p>','')),
               ('tables',SOURCE.replace('−0.25','0.25')),
               ('tables',SOURCE.replace('✓','')),
               ('tables',SOURCE.replace('−0.25 ✓','REPLACE').replace('0.50 †','−0.25 ✓').replace('REPLACE','0.50 †')),
               ('math',SOURCE.replace('<mo>−</mo>','<mo>+</mo>')),
               ('images',SOURCE.replace('<img src="plot.png" alt="Measured outcomes"/>','')),
               ('links',SOURCE.replace('href="#method"','href="#missing"'))]
        for field,damaged in cases:
            with self.subTest(field=field):self.assertIn(field,compare(baseline,read(damaged)))
        self.assertEqual(read(cases[-1][1])['problems'][0]['kind'],'missing_fragment')

    def test_whitespace_between_elements_is_not_content_loss(self):
        self.assertEqual(compare(read(SOURCE),read(SOURCE.replace('><','>\n  <'))),{})

    def test_image_replacement_is_detected(self):
        altered=snapshot({'main.xhtml':SOURCE.encode()},{'plot.png':b'different image'})
        self.assertIn('images',compare(read(SOURCE),altered))

    def test_paragraph_order_is_checked(self):
        changed=SOURCE.replace('first paragraph','TEMP').replace('second paragraph','first paragraph').replace('TEMP','second paragraph')
        self.assertIn('prose',compare(read(SOURCE),read(changed)))


if __name__=='__main__':unittest.main()
