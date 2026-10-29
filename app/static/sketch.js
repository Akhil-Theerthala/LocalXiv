// Excalidraw's hand-drawn look on a Pele SVG. roughjs, the sketch library Excalidraw draws with, redraws each outline
// and line as pencil strokes; fills, text, and arrowheads stay as Pele drew them. The page and papers/mermaid.js both
// call this, so the on-screen figure and the exports get the same strokes. Nested SVGs are $$TeX$$ labels: kept as is.
const GEOMETRY = new Set(['d', 'x', 'y', 'width', 'height', 'rx', 'ry', 'cx', 'cy', 'r', 'points', 'x1', 'y1', 'x2', 'y2',
  'fill', 'fill-opacity']);

function roundedRect(x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2), arc = `A${r},${r} 0 0 1`;
  return `M${x + r},${y}H${x + width - r}${arc} ${x + width},${y + r}V${y + height - r}${arc} ${x + width - r},${y + height}`
    + `H${x + r}${arc} ${x},${y + height - r}V${y + r}${arc} ${x + r},${y}Z`;
}

export function sketch(svg, rough) {
  const generator = rough.generator();
  let seed = 0;
  const open = svg.indexOf('>') + 1;
  return svg.slice(0, open) + svg.slice(open).split(/(<svg\b[\s\S]*?<\/svg>)/).map((part, index) => index % 2 ? part
    : part.replace(/<(rect|polygon|polyline|path|circle|ellipse|line)\b([^>]*?)\/>/g, (element, tag, text) => {
      const a = Object.fromEntries([...text.matchAll(/([\w:-]+)="([^"]*)"/g)].map(match => [match[1], match[2]]));
      if (a.stroke === 'none' || /\bpele-marker\b/.test(a.class || '')) return element;
      const n = name => parseFloat(a[name]) || 0;
      const points = (a.points || '').trim().split(/[\s,]+/).map(Number).reduce((pairs, value, i) =>
        i % 2 ? (pairs[pairs.length - 1].push(value), pairs) : [...pairs, [value]], []);
      // A fixed seed per shape, so each redraw of a figure draws the same strokes. Fixed vertices keep arrow tips on
      // their arrowheads.
      const options = {seed: ++seed, roughness: 1, preserveVertices: true};
      const drawable = tag === 'path' ? generator.path(a.d || '', options)
        : tag === 'rect' ? n('rx') ? generator.path(roundedRect(n('x'), n('y'), n('width'), n('height'), n('rx')), options)
          : generator.rectangle(n('x'), n('y'), n('width'), n('height'), options)
        : tag === 'polygon' ? generator.polygon(points, options)
        : tag === 'polyline' ? generator.linearPath(points, options)
        : tag === 'circle' ? generator.circle(n('cx'), n('cy'), 2 * n('r'), options)
        : tag === 'ellipse' ? generator.ellipse(n('cx'), n('cy'), 2 * n('rx'), 2 * n('ry'), options)
        : generator.line(n('x1'), n('y1'), n('x2'), n('y2'), options);
      const d = generator.toPaths(drawable).map(path => path.d).join(' ');
      const rest = Object.entries(a).filter(([name]) => !GEOMETRY.has(name)).map(([name, value]) => ` ${name}="${value}"`).join('');
      // The shape keeps its fill, which may come from its group, and the sketch takes its stroke, also from its group.
      const fill = a.fill === 'none' ? '' : element.replace(/\sstroke="[^"]*"/, '').replace(/\s*\/>$/, ' stroke="none"/>');
      return fill + `<path d="${d}" fill="none"${rest}/>`;
    })).join('');
}
