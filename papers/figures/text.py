"""SVG text helpers shared by the renderer and the node classes.

A Scene writes math as plain text: ``d_k``, ``W_{out}``, and ``PE_(pos, 2i)`` are subscripts;
``K^T``, ``x^{2i}``, and ``10000^(2i/d_model)`` are superscripts; Unicode script characters such
as ``λ₁`` and ``x²`` mean the same. ``runs`` reads that notation into runs of base and script
text, which the measurer adds up and ``_text`` draws as raised or lowered tspans.
"""
import html
import re
from dataclasses import dataclass

from papers.figures.layout import BODY

SCRIPT_SCALE = 0.75
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
    text: str
    rise: float = 0.0
    script: bool = False


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


def runs(text):
    """The base and script runs of one line of Scene text, adjacent runs of one kind merged."""
    merged = []
    for run in _parse(_SQRT.sub('√', str(text)), 0.0, False):
        if merged and (merged[-1].rise, merged[-1].script) == (run.rise, run.script):
            merged[-1] = Run(merged[-1].text + run.text, run.rise, run.script)
        else:
            merged.append(run)
    return merged


def words(text):
    """``text`` split at whitespace, except inside the bracket group of a script."""
    text = ' '.join(str(text).split())
    result, start, index = [], 0, 0
    while index < len(text):
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
    """The inner SVG of a text element: the escaped string, or tspans when it has math scripts."""
    pieces = runs(text)
    if all(not run.script for run in pieces):
        return esc(''.join(run.text for run in pieces))
    out, rise = [], 0.0
    for run in pieces:
        attributes = ' data-math=""'
        if run.rise != rise:
            attributes += f' dy="{(rise - run.rise) * size:g}"'
            rise = run.rise
        if run.script:
            attributes += f' font-size="{size * SCRIPT_SCALE:g}" data-script=""'
        out.append(f'<tspan{attributes}>{esc(run.text)}</tspan>')
    return ''.join(out)


def _text(x, y, text, *, size=BODY, weight=None, fill=None, anchor=None):
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    if fill:
        attributes += f' fill="{fill}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    return f'<text {attributes}>{content(text, size)}</text>'
