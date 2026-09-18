"""Text measurement for layout. Production measures in WebKit; tests use fixed widths."""
import shutil
import tempfile

from papers.html_figures import measure_text_widths

BODY = 14


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
