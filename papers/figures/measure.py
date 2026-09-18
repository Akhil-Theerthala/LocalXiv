"""Text measurement for layout. Production measures in WebKit; tests use fixed widths."""
import html
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

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
    executable = os.environ.get('LOCALXIV_HTML_RENDERER') or str(Path(__file__).resolve().parent.parent / 'html-snapshot')
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
    """Measure every string once per size and weight in the renderer's font.

    Measurement pages go to a private temporary directory that ``close`` removes.
    """

    def __init__(self, directory):
        self.directory = tempfile.mkdtemp(prefix='measure-', dir=str(directory))
        self.cache = {}

    def close(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _measure(self, strings, size, weight):
        return measure_text_widths(self.directory, strings, font_size=size, font_weight=weight)

    def width(self, text, size=BODY, weight=None):
        key = (text, size, weight)
        if key not in self.cache:
            self.cache[key] = self._measure([text], size, weight)[0]
        return self.cache[key]

    def prime(self, strings, size=BODY, weight=None):
        missing = [text for text in dict.fromkeys(strings) if (text, size, weight) not in self.cache]
        if missing:
            for text, value in zip(missing, self._measure(missing, size, weight)):
                self.cache[(text, size, weight)] = value

    def wrap(self, text, width, size=BODY, weight=None):
        words = str(text).split()
        self.prime(words, size, weight)
        space = self.width(' ', size, weight)
        lines, current, used = [], [], 0.0
        for word in words:
            size_of = self.width(word, size, weight)
            if current and used + space + size_of > width:
                lines.append(' '.join(current))
                current, used = [], 0.0
            current.append(word)
            used += (space if used else 0.0) + size_of
        if current:
            lines.append(' '.join(current))
        return lines or ['']


class FixedMeasurer(Measurer):
    """Widths from character counts, for layout tests that need no renderer."""

    def __init__(self):
        self.cache = {}

    def close(self):
        pass

    def _measure(self, strings, size, weight):
        factor = 0.60 if weight == 700 else 0.55
        return [len(text) * size * factor for text in strings]
