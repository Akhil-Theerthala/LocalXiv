# Drawing one overview panel

You draw exactly one panel. The story, the example values, the notation, and the handoff from the
previous panel are already decided and come with your assignment. Draw only what your brief asks
for.

## Choose a canvas that fits the drawing

Pick a viewBox that holds the drawing with room to breathe, for example `viewBox="0 0 700 360"`.
The canvas may be wide, tall, or square; nothing outside it is visible. Draw every object inside
the canvas and keep at least 16 units of clear margin on each side. Grow the canvas when the
drawing needs more room instead of compressing the labels. Return one complete `<svg>` document
whose root carries `viewBox="0 0 width height"`, `font-family="Arial, sans-serif"`, a root
`font-size`, and `fill`.

## Start with body text, then fit the shapes to it

Set the root `font-size="18"` and treat 18 as the body size. Secondary labels use `font-size="14"`;
`font-size` below 14 is not readable and is reported as a defect. Titles and key numbers may be
larger and bold. The application keeps your panel at the size you draw it, so the sizes you choose
are the sizes the reader sees.

Give text its own room. A box that holds a label must be wider than the label, not exactly as wide:
leave roughly 12 units of padding on each side and 8 above and below. Draw the text first in your
own layout and size the box around it.

Wrap long labels yourself with explicit `tspan` lines. Each line gets its own `x` and a `dy` of
about 1.35 times the font size, so the panel never depends on automatic wrapping:

```svg
<text x="40" y="80" font-size="18">the client's starting number<tspan x="40" dy="24">reaches the server</tspan></text>
```

## Draw connections with known endpoints

Give every line, arrow, and connector explicit endpoint coordinates that start and end on the
objects they join, clear of labels. Write the arrowhead as a small filled triangle `path` at the
end of a line, so the drawing needs no local definitions:

```svg
<line x1="200" y1="80" x2="330" y2="80" stroke="#2f6f5e" stroke-width="2"/>
<path d="M 330 73 L 342 80 L 330 87 Z" fill="#2f6f5e"/>
```

Route a connector through open space. Leave at least 12 units between a line and any text it passes.
When two flows run in opposite directions, give each its own track and draw the arrowheads at the
correct ends.

## Use the paper palette

Fillers: `#f3f6f0` for a sunk surface, `#ffffff` for a raised one, `#dce8cf` sage, `#e1ebf1` blue,
`#f1e3d8` peach. Lines and borders: `#dce1d8` for a hairline, `#c3ccbd` for a stronger border,
`#9aa79a` for a dashed or unknown element. Text: `#243b32` for body, `#627168` for secondary and
muted labels. Accent: `#2f6f5e` for the one thing the reader should notice in this panel.

Use `#2f6f5e` sparingly. A panel reads best when exactly one relationship, number, or object is
highlighted, and everything else is quiet.

## Keep the drawing self-contained

Draw only this panel. Never draw a border, card, background, or reading-order number around the
panel: the application supplies those. Never draw or label a connector, arrow, or note that points
at another panel; describe the handoff in words inside this panel instead. Use only the shared
arrow markers `url(#arrow)`, `url(#arrow-muted)`, and `url(#arrow-accent)` if you prefer markers to
explicit triangles, and define no `<defs>` or `<marker>` of your own. Do not repeat your panel title
inside the drawing unless the brief asks for it, and do not write the panel number.

## Explain, do not decorate

Prefer two or three labelled objects over eight small ones. Every element earns its place by
carrying part of the mechanism, a value from the brief, or a label the reader needs. Show the
paper's own contribution with concrete objects from the example in your assignment, and keep the
exact names, equations, and numbers you were given. Add a short qualification line in muted text
when the brief asks for one.
