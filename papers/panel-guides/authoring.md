# Drawing one overview panel

You draw exactly one panel. The story, the labels, and the relations are decided and come with
your assignment. Draw what the assignment lists and nothing more.

## Explain, do not decorate

The labels are the whole text of the drawing. Give each label its own `text` element with the
exact words, grouping, signs, operators, and units the assignment gives; the check rejects a
missing or changed label. Show each relation as an arrow or as alignment between the two labelled
objects, with the relation's short label on the arrow when it has one. The note, when there is
one, is one line of muted text. Draw no other text: no title, no caption, no explanation, no
sentence in a box. The application draws the heading above the panel and the explanation around
the figure, and it rejects a panel with more visible words than its assignment supports.

Prefer a few large labelled objects over many small ones. Every shape earns its place by
carrying a label or showing a relation. When a defect needs fixing, remove before you add: delete
text that is not on the assignment, drop decoration, merge boxes that carry one idea, and wrap a
long label into lines. Enlarge the canvas only when removal and wrapping cannot fix it.

## Choose a canvas, then let the application scale it

Pick a `viewBox` that holds the drawing with room to breathe, for example `viewBox="0 0 700 360"`.
The application scales the whole panel to the reader's column, so a wider drawing shows smaller
text and a narrower one larger. Keep the panel wider than it is tall. Draw every object inside the
canvas with at least 16 units of clear margin on each side. Return one complete `<svg>` document
whose root carries `viewBox="0 0 width height"`, `font-family="Arial, sans-serif"`, a root
`font-size`, and `fill`.

## Start with the text, then fit the shapes to it

Set the root `font-size="18"` and use 18 for every label. Use `font-size="14"` only for a relation
label or the note; smaller text is rejected. A key number or name may be larger and bold.

Give text its own room. A box that holds a label is wider than the label: leave about 12 units of
padding on each side and 8 above and below. Place the text first, then size the box around it.

Wrap a long label yourself with explicit `tspan` lines. Each line gets its own `x` and a `dy` of
about 1.35 times the font size:

```svg
<text x="40" y="80" font-size="18">Multi-Head Self-Attention<tspan x="40" dy="24">all tokens attend mutually</tspan></text>
```

## Draw connections with known endpoints

Give every arrow explicit endpoint coordinates that start and end on the objects it joins, clear
of their text. Write the arrowhead as a small filled triangle `path` at the end of a line, or use
the shared markers `url(#arrow)`, `url(#arrow-muted)`, and `url(#arrow-accent)`; define no
`<defs>` or `<marker>` of your own.

```svg
<line x1="200" y1="80" x2="330" y2="80" stroke="#2f6f5e" stroke-width="2"/>
<path d="M 330 73 L 342 80 L 330 87 Z" fill="#2f6f5e"/>
```

Route a connector through open space and keep 12 units between a line and any text it passes.
When two flows run in opposite directions, give each its own track.

## Use the paper palette

Fills: `#f3f6f0` for a sunk surface, `#ffffff` for a raised one, `#dce8cf` sage, `#e1ebf1` blue,
`#f1e3d8` peach. Lines: `#dce1d8` hairline, `#c3ccbd` stronger border, `#9aa79a` dashed or
unknown. Text: `#243b32` body, `#627168` muted. Accent `#2f6f5e` for the one thing the reader
should notice in this panel; use it once.

## Write equations in plain notation

There is no math renderer. Reproduce an equation label exactly as the assignment writes it, with
`Σ ≥ ≤ √ · × → α π σ` as characters, a fraction as `a / b`, and a subscript as plain text
(`d_k`, `x_i`). One equation per `text` element, at body size or larger.

## Keep the drawing self-contained

Draw only this panel. Never draw a border, card, background, heading, or reading-order number
around it, and never draw an arrow or note that points at another panel.
