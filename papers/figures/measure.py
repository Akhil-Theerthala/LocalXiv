"""Text measurement for layout, in the WebKit text stack that draws the figure."""
import html
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from papers.figures.layout import BODY
from papers.figures.text import EQUATION_PAD, MATH_FONT, SCRIPT_SCALE, runs, words

FONT_FAMILY = 'Arial, sans-serif'


def _snapshot(target, mode, style, body, timeout):
    """Write ``body`` as an HTML page in render ``mode`` beside ``target``, run the native renderer
    on it, and return the checks it writes."""
    target.with_suffix('.html').write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="localxiv-render-mode" content="' + mode + '">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<style>' + style + '</style></head><body>' + body + '</body></html>')
    executable = (os.environ.get('LOCALXIV_HTML_RENDERER')
                  or str(Path(__file__).resolve().parent.parent / 'html-snapshot'))
    if not Path(executable).is_file():
        raise ValueError('HTML renderer is missing. Build papers/HTMLSnapshot.swift as papers/html-snapshot '
                         '(see development instructions).')
    result = subprocess.run([executable, str(target.with_suffix('.html')), str(target)],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise ValueError('HTML rendering failed: ' + result.stderr[-1000:])
    return json.loads(target.with_suffix('.checks.json').read_text())


class Measurer:
    """Measure every run once per size, weight, and font family in the renderer's fonts.

    Measurement pages go to a private temporary directory that ``close`` removes.
    """

    def __init__(self, directory):
        self.directory = tempfile.mkdtemp(prefix='measure-', dir=str(directory))
        self.cache = {}

    def close(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _measure(self, strings, size, weight, family):
        """Measure rendered text widths in the same WebKit text stack the figure renderer uses.

        Application-owned wrapping measures each word once and adds them with the space width, so a
        simple recovery panel wraps exactly as the rasterizer will draw it. Bold text measures wider
        than regular text, so the weight must be measured with the same value it is drawn with.
        """
        spans = ''.join('<span data-key="' + str(index) + '">' + html.escape(value) + '</span>'
                        for index, value in enumerate(strings))
        weight_style = ('font-weight:' + str(weight) + ';') if weight else ''
        checks = _snapshot(Path(self.directory) / ('measure-' + uuid.uuid4().hex), 'measure',
                           '*{box-sizing:border-box}html,body{margin:0;padding:0}main{font-family:' + family
                           + ';font-size:' + str(size) + 'px;' + weight_style + 'white-space:nowrap}'
                           'span{display:inline-block;white-space:pre}', '<main>' + spans + '</main>', 120)
        widths = {int(item['key']): float(item['width']) for item in checks.get('widths', [])}
        return [widths.get(index, 0.0) for index in range(len(strings))]

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
