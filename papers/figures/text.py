"""SVG text helpers shared by the renderer and the node classes.

A Scene writes math as plain text: ``d_k``, ``W_{out}``, and ``PE_(pos, 2i)`` are subscripts;
``K^T``, ``x^{2i}``, and ``10000^(2i/d_model)`` are superscripts; Unicode script characters such
as ``λ₁`` and ``x²`` mean the same. ``runs`` reads that notation into runs of base and script
text, which the measurer adds up and ``_text`` draws as raised or lowered tspans. A Scene wraps
each equation in backticks: its runs are ``math``, drawn in the math font inside a faint box, and
never split across lines.
"""
import html
import re
from dataclasses import dataclass
from itertools import groupby

from papers.figures.layout import BODY

SCRIPT_SCALE = 0.75
MATH_FONT = "'STIX Two Math', 'STIX Two Text', 'Times New Roman', serif"
# The equation box: padding in units on each side of its text, then its top above the baseline and its
# height, in units of the font size.
EQUATION_PAD = 4
EQUATION_TOP, EQUATION_HEIGHT = 0.9, 1.28
# Rise of a script run's baseline, in units of the base font size.
RISE = {'^': 0.38, '_': -0.22}
_SUPERSCRIPTS = dict(zip('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿᵀᵗᴼᵏᵈᵃᵇᶜᵉʰʲˡᵐᵒᵖʳˢᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴾᴿᵁⱽᵂ',
                         '0123456789+-=()inTtOkdabcehjlmoprsuvwxyzABDEGHIJKLMNPRUVW'))
_SUBSCRIPTS = dict(zip('₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₔₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ', '0123456789+-=()aeoxəhklmnpstijruv'))
_UNICODE_SCRIPT = re.compile('[' + ''.join(_SUPERSCRIPTS) + ''.join(_SUBSCRIPTS) + ']+')
_WORD = re.compile(r'[+\-−]?[^\W_]+|[*′⊤†]')
_SQRT = re.compile(r'\bsqrt(?=\()')
_CLOSE = {'{': '}', '(': ')'}


@dataclass(frozen=True)
class Run:
    """One stretch of text drawn at one rise and size. ``math`` runs belong to an equation: each
    maximal sequence of them is one equation box."""
    text: str
    rise: float = 0.0
    script: bool = False
    math: bool = False


def _group(text, start):
    """The index after the bracket group that opens at ``start``, or None when it never closes."""
    opening, depth = text[start], 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == _CLOSE[opening]:
            depth -= 1
            if not depth:
                return index + 1
    return None


def _script_end(text, start):
    """Where the script that follows the marker at ``start - 1`` ends, or None for a plain character."""
    if start < len(text) and text[start] in _CLOSE:
        return _group(text, start)
    match = _WORD.match(text, start)
    return match.end() if match else None


def _parse(text, rise, script):
    runs, plain, index = [], [], 0

    def flush():
        if plain:
            runs.append(Run(''.join(plain), rise, script))
            plain.clear()

    while index < len(text):
        char = text[index]
        if char in RISE and index and not text[index - 1].isspace():
            end = _script_end(text, index + 1)
            if end is not None:
                flush()
                body = text[index + 1:end]
                if body[:1] in _CLOSE:
                    body = body[1:-1]
                runs += _parse(body, rise + RISE[char] * (SCRIPT_SCALE if script else 1), True)
                index = end
                continue
        match = _UNICODE_SCRIPT.match(text, index)
        if match and index:
            flush()
            for glyph in match.group():
                marker = '^' if glyph in _SUPERSCRIPTS else '_'
                runs.append(Run((_SUPERSCRIPTS if marker == '^' else _SUBSCRIPTS)[glyph],
                                rise + RISE[marker] * (SCRIPT_SCALE if script else 1), True))
            index = match.end()
            continue
        plain.append(char)
        index += 1
    flush()
    return runs


def _closing(text, index):
    """The index of the backtick that closes the one at ``index``, or None when it is plain text."""
    end = text.find('`', index + 1) if text[index] == '`' else -1
    return end if end > index + 1 else None


def runs(text):
    """The base and script runs of one line of Scene text, adjacent runs of one kind merged.

    A backtick pair marks an equation: its runs are ``math``, and the backticks are not drawn.
    """
    text, pieces, start, index = _SQRT.sub('√', str(text)), [], 0, 0
    while index < len(text):
        end = _closing(text, index)
        if end is None:
            index += 1
            continue
        pieces += _parse(text[start:index], 0.0, False)
        pieces += [Run(run.text, run.rise, run.script, True) for run in _parse(text[index + 1:end], 0.0, False)]
        start = index = end + 1
    pieces += _parse(text[start:], 0.0, False)
    merged = []
    for run in pieces:
        if merged and (merged[-1].rise, merged[-1].script, merged[-1].math) == (run.rise, run.script, run.math):
            merged[-1] = Run(merged[-1].text + run.text, run.rise, run.script, run.math)
        else:
            merged.append(run)
    return merged


def words(text):
    """``text`` split at whitespace, except inside an equation or the bracket group of a script."""
    text = ' '.join(str(text).split())
    result, start, index = [], 0, 0
    while index < len(text):
        end = _closing(text, index)
        if end is not None:
            index = end + 1
            continue
        if text[index] in RISE and index and not text[index - 1].isspace() and text[index + 1:index + 2] in _CLOSE:
            end = _group(text, index + 1)
            if end is not None:
                index = end
                continue
        if text[index] == ' ':
            result.append(text[start:index])
            start = index + 1
        index += 1
    if start < len(text):
        result.append(text[start:])
    return result


def esc(value):
    return html.escape(str(value), quote=True)


def content(text, size=BODY):
    """The inner SVG of a text element: the escaped string, or tspans when it has math.

    An equation's tspans take the math font at regular weight, and ``dx`` opens and closes the
    padding of its box, so the drawn line is as wide as ``Measurer.width`` says.
    """
    pieces = runs(text)
    if all(not run.script and not run.math for run in pieces):
        return esc(''.join(run.text for run in pieces))
    out, rise, math = [], 0.0, False
    for run in pieces:
        attributes = ' data-math=""'
        if run.math != math:
            attributes += f' dx="{EQUATION_PAD}"'
            math = run.math
        if run.rise != rise:
            attributes += f' dy="{(rise - run.rise) * size:g}"'
            rise = run.rise
        if run.math:
            # Equations take the page's text colour, not a muted line's grey: grey on the box's
            # tint fell below 4.5:1 on green and peach cards.
            attributes += f' font-family="{esc(MATH_FONT)}" font-weight="400" fill="currentColor"'
        if run.script:
            attributes += f' font-size="{size * SCRIPT_SCALE:g}" data-script=""'
        out.append(f'<tspan{attributes}>{esc(run.text)}</tspan>')
    return ''.join(out)


_ANCHOR = {'middle': 0.5, 'end': 1.0}


def equation_boxes(x, y, text, measure, *, size=BODY, weight=None, anchor=None):
    """The equation boxes behind one line of text drawn at ``x``, ``y``.

    A box has no fill of its own: it takes the SVG's text colour at low opacity, a faint tint of
    the ink on any card in either palette. ``data-equation`` tells the native checks it is not a
    text container.
    """
    pieces = runs(text)
    if not any(run.math for run in pieces):
        return ''
    left = x - measure.width(text, size, weight) * _ANCHOR.get(anchor, 0.0)
    out = []
    for math, group in groupby(pieces, key=lambda run: run.math):
        span = sum(measure.run_width(run, size, weight) for run in group) + (2 * EQUATION_PAD if math else 0.0)
        if math:
            out.append(f'<rect data-equation="" x="{left:g}" y="{y - EQUATION_TOP * size:g}" width="{span:g}" '
                       f'height="{EQUATION_HEIGHT * size:g}" rx="3" fill-opacity="0.08"/>')
        left += span
    return ''.join(out)


def _text(x, y, text, *, size=BODY, weight=None, fill=None, anchor=None, measure=None):
    """One line of text; with ``measure``, its equations get their boxes."""
    drawn = equation_boxes(x, y, text, measure, size=size, weight=weight, anchor=anchor) if measure else ''
    if anchor in _ANCHOR:
        # WebKit anchors a line by its glyph advance and adds each ``dx`` after, so move the line
        # back by its box padding: the line and its boxes then sit where the measured width says.
        spans = sum(1 for math, _ in groupby(runs(text), key=lambda run: run.math) if math)
        x -= 2 * EQUATION_PAD * spans * _ANCHOR[anchor]
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    if fill:
        attributes += f' fill="{fill}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    return drawn + f'<text {attributes}>{content(text, size)}</text>'
