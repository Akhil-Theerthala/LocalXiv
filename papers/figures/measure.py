"""Text measurement for layout. Production measures in WebKit; tests use fixed widths."""
import html
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from papers.figures.text import EQUATION_PAD, MATH_FONT, SCRIPT_SCALE, runs, words

BODY = 14
FONT_FAMILY = 'Arial, sans-serif'


def measure_text_widths(directory, strings, *, font_size=18, font_family=FONT_FAMILY,
                        font_weight=None):
    """Measure rendered text widths in the same WebKit text stack the figure renderer uses.

    Application-owned wrapping measures each word once and adds them with the space width, so a
    simple recovery panel wraps exactly as the rasterizer will draw it. Bold text measures wider
    than regular text, so the weight must be measured with the same value it is drawn with.
    """
    strings = [str(value) for value in strings]
    if not strings:
        return []
    target = Path(directory) / ('measure-' + uuid.uuid4().hex)
    target.parent.mkdir(parents=True, exist_ok=True)
    spans = ''.join('<span data-key="' + str(index) + '">' + html.escape(value) + '</span>'
                    for index, value in enumerate(strings))
    weight_style = ('font-weight:' + str(font_weight) + ';') if font_weight else ''
    page = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="localxiv-render-mode" content="measure">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<style>*{box-sizing:border-box}html,body{margin:0;padding:0}'
            'main{font-family:' + font_family + ';font-size:' + str(font_size) + 'px;'
            + weight_style + 'white-space:nowrap}'
            'span{display:inline-block;white-space:pre}</style></head><body><main>' + spans + '</main></body></html>')
    target.with_suffix('.html').write_text(page)
    executable = (os.environ.get('LOCALXIV_HTML_RENDERER')
                  or str(Path(__file__).resolve().parent.parent / 'html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot '
                         '(see development instructions).')
    result = subprocess.run([executable, str(target.with_suffix('.html')), str(target)],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError('HTML text measurement failed: ' + result.stderr[-1000:])
    checks = json.loads(target.with_suffix('.checks.json').read_text())
    widths = {int(item['key']): float(item['width']) for item in checks.get('widths', [])}
    return [widths.get(index, 0.0) for index in range(len(strings))]



class Measurer:
    """Measure every run once per size, weight, and font family in the renderer's fonts.

    Measurement pages go to a private temporary directory that ``close`` removes.
    """

    def __init__(self, directory):
        self.directory = tempfile.mkdtemp(prefix='measure-', dir=str(directory))
        self.cache = {}

    def close(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _measure(self, strings, size, weight, family=FONT_FAMILY):
        return measure_text_widths(self.directory, strings, font_size=size, font_weight=weight, font_family=family)

    @staticmethod
    def _key(run, size, weight):
        """The cache key of one run: an equation is regular weight in the math font; a script is smaller."""
        return (run.text, size * SCRIPT_SCALE if run.script else size,
                None if run.math else weight, MATH_FONT if run.math else FONT_FAMILY)

    def run_width(self, run, size=BODY, weight=None):
        """The drawn width of one run of a line drawn at ``size`` and ``weight``."""
        key = self._key(run, size, weight)
        if key not in self.cache:
            self.prime_keys([key])
        return self.cache[key]

    def width(self, text, size=BODY, weight=None):
        """The drawn width: the sum of its runs, each at the size and font it is drawn in, plus the
        padding on both sides of each equation box."""
        pieces = runs(text)
        boxes = sum(1 for index, run in enumerate(pieces) if run.math and not (index and pieces[index - 1].math))
        return sum(self.run_width(run, size, weight) for run in pieces) + 2 * EQUATION_PAD * boxes

    def prime_keys(self, keys):
        """Measure the missing keys, one renderer call per size, weight, and family."""
        missing = {}
        for text, size, weight, family in dict.fromkeys(keys):
            if (text, size, weight, family) not in self.cache:
                missing.setdefault((size, weight, family), []).append(text)
        for (size, weight, family), texts in missing.items():
            for text, value in zip(texts, self._measure(texts, size, weight, family)):
                self.cache[(text, size, weight, family)] = value

    def prime(self, strings, size=BODY, weight=None):
        self.prime_keys([self._key(run, size, weight) for text in strings for run in runs(text)])

    def wrap(self, text, width, size=BODY, weight=None):
        whole = ' '.join(words(text))
        if not whole:
            return ['']
        # The card was sized from this same whole-string measurement, so a string that fits
        # whole stays on one line even when its words plus spaces add up 0.01 wider.
        if self.width(whole, size, weight) <= width:
            return [whole]
        parts = words(whole)
        self.prime(parts, size, weight)
        space = self.width(' ', size, weight)
        lines, current, used = [], [], 0.0
        for word in parts:
            size_of = self.width(word, size, weight)
            if current and used + space + size_of > width:
                lines.append(' '.join(current))
                current, used = [], 0.0
            current.append(word)
            used += (space if used else 0.0) + size_of
        if current:
            lines.append(' '.join(current))
        return lines


class FixedMeasurer(Measurer):
    """Widths from character counts, for layout tests that need no renderer."""

    def __init__(self):
        self.cache = {}

    def close(self):
        pass

    def _measure(self, strings, size, weight, family=FONT_FAMILY):
        factor = 0.60 if weight == 700 else 0.55
        return [len(text) * size * factor for text in strings]
