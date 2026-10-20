// The one text of a passage, in the browser: the text that papers/document.py _text() builds, so a stored quote is found
// again in the Paper and in the library row. This module imports nothing, so that Node can load it for
// tests/one_text_parity.mjs, which checks every corpus passage against the Python text.
const MATHML = 'http://www.w3.org/1998/Math/MathML';
// The characters that Python's str.split() collapses (str.isspace). The JavaScript \s set differs from it.
const SPACE = /[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/;
const isMath = element => element.namespaceURI === MATHML && element.localName === 'math';

// A formula's TeX, as papers/document.py _tex() reads it: '' when there is none.
export function tex(math) {
  return math.getAttribute('alttext')
    || [...math.getElementsByTagNameNS('*', 'annotation')].find(note => note.getAttribute('encoding') === 'application/x-tex')?.textContent || '';
}

// The text of `root` as papers/document.py _text() builds it: each formula inside is " $tex$ ", and whitespace
// collapses to one space with none at the ends. A root that is a formula gives "$tex$" with no change at all.
// `map[i]` is where character i comes from: [text node, offset], or the formula's math element, so that a selection
// edge inside a formula takes the whole formula. Both count UTF-16 units, as `text` does.
export function textMap(root) {
  const source = isMath(root) ? tex(root) : '';
  if (source) { const text = `$${source}$`; return {text, map: new Array(text.length).fill(root)}; }
  let text = '', space = null;
  const map = [];
  const add = (char, from) => {
    if (SPACE.test(char)) { space ??= from; return; }
    if (space && text) { text += ' '; map.push(space); }
    space = null; text += char; map.push(from);
  };
  const formula = math => {
    const own = tex(math), value = own ? ` $${own}$ ` : ` ${math.textContent} `;
    for (let at = 0; at < value.length; at++) add(value[at], math);
  };
  const walk = parent => {
    for (const child of parent.childNodes) {
      if (child.nodeType === Node.TEXT_NODE || child.nodeType === Node.CDATA_SECTION_NODE) {
        for (let offset = 0; offset < child.data.length; offset++) add(child.data[offset], [child, offset]);
      } else if (child.nodeType !== Node.ELEMENT_NODE) continue;
      else if (isMath(child)) formula(child);
      else walk(child);
    }
  };
  if (isMath(root)) formula(root); else walk(root);
  return {text, map};
}

// The place of `quote` in `text` whose surroundings agree with the most characters of `prefix` (read backwards from
// the quote) and `suffix`, or the first place when they agree equally. -1 when the quote is not in `text`.
export function findOffset(text, quote, prefix = '', suffix = '') {
  let best = -1, most = -1;
  for (let at = quote ? text.indexOf(quote) : -1; at >= 0; at = text.indexOf(quote, at + 1)) {
    let before = 0, after = 0;
    while (before < prefix.length && text[at - 1 - before] === prefix[prefix.length - 1 - before]) before++;
    while (after < suffix.length && text[at + quote.length + after] === suffix[after]) after++;
    if (before + after > most) { best = at; most = before + after; }
  }
  return best;
}

// The DOM range of `quote` in `root`, and the formulas in it, or null. A caller that keeps the one text of `root` gives
// it as `oneText`.
// shortcut: a record with no prefix and no suffix (a Release 1 Question card keeps neither) gets the first place, so a
// short quote that is also earlier in the passage marks those earlier words.
export function findWords(root, quote, prefix = '', suffix = '', oneText = textMap(root)) {
  const {text, map} = oneText, start = findOffset(text, quote, prefix, suffix);
  if (start < 0) return null;
  const first = map[start], last = map[start + quote.length - 1], range = root.ownerDocument.createRange();
  if (Array.isArray(first)) range.setStart(...first); else range.setStartBefore(first);
  if (Array.isArray(last)) range.setEnd(last[0], last[1] + 1); else range.setEndAfter(last);
  const formulas = new Set(map.slice(start, start + quote.length).filter(from => !Array.isArray(from)));
  return {range, formulas: [...formulas]};
}
