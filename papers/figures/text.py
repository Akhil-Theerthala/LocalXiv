"""SVG text helpers shared by the renderer and the node classes."""
import html

from papers.figures.layout import BODY


def esc(value):
    return html.escape(str(value), quote=True)


def _text(x, y, text, *, size=BODY, weight=None, fill=None, anchor=None):
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size}"'
    if weight:
        attributes += f' font-weight="{weight}"'
    if fill:
        attributes += f' fill="{fill}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    return f'<text {attributes}>{esc(text)}</text>'
