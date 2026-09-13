# SVG construction notes

Concise notes for the supported subset, written for LocalXiv. The
[W3Schools SVG reference](https://www.w3schools.com/graphics/svg_reference.asp) is the broader
source for the same elements.

## Document and canvas

- `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 360" font-family="Arial, sans-serif" font-size="18" fill="#243b32">`
- `viewBox` is four numbers: `min-x min-y width height`. Local panels always use `0 0 width height`,
  so the numbers in your drawing are canvas units directly.
- One unit is one pixel at the reader's 100% size. Everything outside the viewBox is invisible.
- The root `font-family`, `font-size`, and `fill` are inherited by children; a child overrides them.

## Shapes

- `<rect x="20" y="40" width="200" height="60" rx="8"/>` — `rx`/`ry` round the corners.
- `<circle cx="80" cy="80" r="20"/>`, `<ellipse cx="80" cy="80" rx="24" ry="16"/>`.
- `<line x1="20" y1="40" x2="200" y2="40"/>` — straight connector between two points.
- `<polyline points="20,60 80,20 140,60" fill="none" stroke="#243b32"/>` — open path through points.
- `<polygon points="20,60 80,20 140,60"/>` — closed and filled.
- `<path d="M 20 60 L 80 20 L 140 60 Z"/>` — `M` starts, `L` draws a line, `Z` closes. `H`/`V` move
  horizontally/vertically, `C`/`S` are cubic curves, `Q`/`T` quadratic, `A` an elliptical arc. The
  same letter in lowercase uses relative coordinates.

## Text

- `<text x="40" y="80">Label</text>` — `x`/`y` position the baseline start of the first line.
- `text-anchor="start"` (default), `"middle"`, or `"end"` positions the anchor point along the text.
  With `middle`, `x` is the centre of the label.
- A line break is a `tspan` with its own `x` and `dy`: `<text x="40" y="80">first<tspan x="40" dy="24">second</tspan></text>`.
- `font-size`, `font-weight="bold"`, and `fill` set on a `text` or `tspan` override the inherited
  values. This keeps a value or an equation in the same visual language as the surrounding labels.
- Keep body text at 18 units and secondary text at 14 or more.

## Groups and transforms

- `<g>` groups children so they share attributes or move together.
- `transform="translate(40 20)"` moves a group; `scale(1.2)`, `rotate(90)`, and `skewX(10)` also work.
- Text inside a scaled group shrinks with it, so scale a whole group only when the labels stay at 14
  units or more after the transform.

## Paint

- `fill` colours the inside; `stroke` draws the outline; `fill="none"` keeps a shape open.
- `stroke-width`, `stroke-dasharray="4 3"`, `stroke-linecap="round"`, and `stroke-linejoin="round"`
  shape the outline.
- Colours are literal `#rrggbb`, `rgb(r, g, b)`, `black`, `white`, or `none`. No CSS classes or
  variables.
- `opacity`, `fill-opacity`, and `stroke-opacity` take values from 0 to 1.
- Arrowheads on supported elements use the shared markers `url(#arrow)`, `url(#arrow-muted)`, and
  `url(#arrow-accent)` on `marker-end` or `marker-start`. Prefer a small explicit `path` triangle,
  which always renders identically.

## Not supported

Scripts, events, animation, images, external files, links, `<use>`, CSS, filters, masks, clipping
paths, and local `<defs>`/`<marker>` definitions are rejected. Panels are self-contained: draw the
shapes you need directly, and use the shared markers when you want markers at all.
