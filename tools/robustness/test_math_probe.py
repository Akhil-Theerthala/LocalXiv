import json
import subprocess
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


class MathProbeTests(unittest.TestCase):
    def test_unknown_commands_fail_and_supported_siblings_are_independent(self):
        script=Path(__file__).resolve().parents[2]/'papers/tex_math.js'
        examples=[{'tex':r'\unknownsymbol{x}'},{'tex':r'\enclose{circle}{x}'},{'tex':r'x^2'},
                  {'tex':r'\def\leak{42}\leak'},{'tex':r'\leak'}]
        result=subprocess.run(['node',str(script)],input=json.dumps(examples),capture_output=True,text=True,check=True)
        rows=json.loads(result.stdout)
        self.assertIn('error',rows[0])
        self.assertEqual(ET.fromstring(rows[1]['mathml']).find('.//{*}menclose').get('notation'),'circle')
        self.assertIsNotNone(ET.fromstring(rows[2]['mathml']).find('.//{*}msup'))
        self.assertIn('mathml',rows[3])
        self.assertIn('error',rows[4], 'A macro defined by another expression must not leak')


if __name__=='__main__':unittest.main()
