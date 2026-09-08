"""Regression and metamorphic checks for the small TeX compatibility shim."""
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "papers" / "tex_math.js"


def render(tex):
    result = subprocess.run(
        ["node", str(RENDERER)],
        input=json.dumps([{"tex": tex, "display": False}]),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)[0]


class KnownMathCommandTests(unittest.TestCase):
    def test_known_commands_render(self):
        for tex in (
            r"\textsc{stack\_rows}(x)",
            r"i\textsuperscript{th}",
            r"x\textsubscript{ij}",
            r"\Bar{S}",
            r"\bm{b}",
        ):
            with self.subTest(tex=tex):
                result = render(tex)
                self.assertNotIn("error", result)
                self.assertNotIn("<merror", result["mathml"])

    def test_equivalent_sources_have_equivalent_mathml(self):
        pairs = (
            (r"\hfill \square", r"\square"),
            (r"x\protect\leq y", r"x\leq y"),
            (r"\textsc{stack\_rows}(x)", r"\text{stack\_rows}(x)"),
            (r"i\textsuperscript{th}", r"i^{\text{th}}"),
            (r"x\textsubscript{ij}", r"x_{\text{ij}}"),
            (r"\Bar{S}", r"\overline{S}"),
            (r"\bm{b}", r"\boldsymbol{b}"),
        )
        for source, equivalent in pairs:
            with self.subTest(source=source):
                self.assertEqual(render(source)["mathml"], render(equivalent)["mathml"])

    def test_native_argument_handling_covers_spacing_grouping_and_comments(self):
        pairs = (
            (r"\bm x", r"\boldsymbol x"),
            (r"\Bar {S}", r"\overline{S}"),
            (r"\bm{a\{b\}}", r"\boldsymbol{a\{b\}}"),
            ("\\textsc{a% comment\nb}", r"\text{ab}"),
        )
        for source, equivalent in pairs:
            with self.subTest(source=source):
                self.assertEqual(render(source)["mathml"], render(equivalent)["mathml"])

    def test_unsupported_content_still_rejects(self):
        for tex in (r"\unknownsymbol{x}", r"\bm{a"):
            with self.subTest(tex=tex):
                self.assertIn("error", render(tex))


if __name__ == "__main__":
    unittest.main()
