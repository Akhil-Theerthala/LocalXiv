# LocalXiv diagram authoring

Design guidance adapted from cathrynlavery/diagram-design (MIT),
https://github.com/cathrynlavery/diagram-design; license text in diagram-style.LICENSE.
This is a LocalXiv adaptation, not the complete upstream skill or a claim of passing
its full checklist.

Choose the explanatory relationship before the layout: components and connections,
ordered transformation, branching decision, grouped alternatives, or measured comparison.
Use a concrete example to explain this paper's contribution, never as a replacement for it.
A survey or evaluation needs its actual scope and findings; do not invent a new method.
The reader knows basic ML vocabulary but not paper-specific acronyms.

Use connected panels when the explanation needs multiple levels. Keep at most nine main objects per panel. Delete redundant labels and connections.
Every connection has a meaning. Route connectors through open space, clear of labels and
unrelated objects. Prefer aligned or elbow routes. Place labels beside their relevant objects.
Do not flatten parallel components or feedback into a sequential chain. Charts need units,
baselines and faithful scales. Do not draw measured-looking bars for invented teaching values.

Use the application's built-in paper, ink, muted, sage, blue and peach styles. No shadows,
external fonts, scripts, images, animation or decorative icons. The identity is fixed; the
arrangement follows the explanation. Prefer open space over paragraph cards. Keep SVG labels at least 14px after the full 960px image shrinks to 640px wide.
For a full-width viewBox near 880 units, start with 24–32px labels; scale up for
wider viewBoxes or columns. Leave room for text. HTML handles paragraph wrapping.
Use actual objects from the example, with annotations that explain what changes or differs.

Overview: author one complete SVG teaching scene. The model controls composition, coordinates,
grouping, hierarchy and connectors within the supported SVG profile; the application validates
markup and measures the rendered result. Put explanations beside the objects they explain and a
short qualification below. Show the core operation through an example, how blocks combine or
operate in parallel, and where they fit in the architecture when relevant. Reuse visual symbols
across these levels. Lead with the paper's contribution and show its supported finding in the
scene. There is no target word count; 600 visible SVG words is an extreme rejection ceiling, not
a writing goal. The complete Overview must fit 960px width by at most 960px height. Cut repetition
and secondary detail before tightening spacing. Preserve readable labels and essential connections.
Blog: write connected prose at the selected length, adding 0–3 figures only when they teach
a relationship better than prose. Introduce each figure and explain what readers should notice.
Label invented examples locally. Never present them as the paper's experimental results.
