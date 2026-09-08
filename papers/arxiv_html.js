/* Parse the article only without executing page scripts. */
const fs = require('node:fs');
const {DOMParser, XMLSerializer, DOMImplementation} = require('@xmldom/xmldom');
const X = 'http://www.w3.org/1999/xhtml';
const M = 'http://www.w3.org/1998/Math/MathML';
const S = 'http://www.w3.org/2000/svg';
const {html, title} = JSON.parse(fs.readFileSync(0, 'utf8'));
const articles = html.match(/<article\b[\s\S]*?<\/article>/g) || [];
if (articles.length !== 1) throw new Error('Expected one arXiv article.');
const doc = new DOMParser({onError: (_, message) => { throw new Error(message); }})
  .parseFromString(articles[0], 'text/html');
const article = doc.documentElement;
if (!article.getAttribute('class').split(/\s+/).includes('ltx_document')) {
  throw new Error('The page does not contain an arXiv paper.');
}
const out = new DOMImplementation().createDocument(X, 'html', null);
const head = out.createElementNS(X, 'head');
out.documentElement.appendChild(head);
const heading = out.createElementNS(X, 'title');
heading.textContent = title;
head.appendChild(heading);
const body = out.createElementNS(X, 'body');
out.documentElement.appendChild(body);
let intents = 0;
const blocks = new Set(['div', 'p', 'table', 'figure', 'section', 'ol', 'ul', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
function clone(node, ns) {
  if (node.nodeType !== 1) return out.importNode(node, true);
  if (node.localName === 'math') ns = M;
  if (node.localName === 'svg') ns = S;
  const children = Array.from(node.childNodes);
  // LaTeXML's transformed wrapper can contain paragraphs, so it is a block.
  const element = out.createElementNS(ns, node.localName);
  for (const attribute of Array.from(node.attributes)) {
    if (attribute.name.startsWith('xmlns')) continue;
    // EPUB uses MathML 3. Keep the original MathML 4 hints in the retained HTML.
    if (ns === M && attribute.name === 'intent') { intents++; continue; }
    element.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
  }
  const mathText = ns === M && ['mi', 'mo', 'mn', 'ms', 'mtext'].includes(node.localName);
  const childNS = mathText || node.localName === 'foreignObject' ||
    (node.localName === 'annotation-xml' && ['text/html', 'application/xhtml+xml'].includes(node.getAttribute('encoding')))
    ? X : ns;
  for (const child of children) element.appendChild(clone(child,
    mathText && ['mglyph', 'malignmark'].includes(child.localName) ? M : childNS));
  if (ns === X && node.localName === 'figure') {
    const content = Array.from(element.childNodes);
    const captions = content.filter(c => c.nodeType === 1 && c.localName === 'figcaption');
    const substantive = c => c.nodeType === 1 || (c.nodeType === 3 && c.data.trim());
    if (captions.length > 1) {
      const group = out.createElementNS(X, 'div');
      for (const attribute of Array.from(element.attributes)) group.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
      const captionFirst = content.find(substantive) === captions[0];
      let figure = null;
      for (const child of content) {
        const caption = captions.includes(child);
        if (!figure && !substantive(child)) { group.appendChild(child); continue; }
        if (!figure || (captionFirst && caption)) {
          figure = out.createElementNS(X, 'figure');
          group.appendChild(figure);
        }
        figure.appendChild(child);
        if (!captionFirst && caption) figure = null;
      }
      return group;
    }
    if (captions.length === 1) {
      const index = content.indexOf(captions[0]);
      if (content.slice(0, index).some(substantive) && content.slice(index + 1).some(substantive)) {
        // EPUB requires a caption at either end. Keep following notes in place.
        const group = out.createElementNS(X, 'div');
        for (const attribute of Array.from(element.attributes)) group.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
        const figure = out.createElementNS(X, 'figure');
        group.appendChild(figure);
        content.forEach((child, i) => (i <= index ? figure : group).appendChild(child));
        return group;
      }
    }
  }
  const hasBlocks = Array.from(element.childNodes).some(c => c.nodeType === 1 && blocks.has(c.localName));
  if (ns === X && ['span', 'p'].includes(node.localName) && hasBlocks) {
    const wrapper = out.createElementNS(X, 'div');
    for (const attribute of Array.from(element.attributes)) wrapper.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
    if (node.localName === 'span') {
      while (element.firstChild) wrapper.appendChild(element.firstChild);
    } else {
      // Keep each prose run in a paragraph so passage extraction retains it.
      let paragraph = null;
      for (const child of Array.from(element.childNodes)) {
        if (child.nodeType === 1 && blocks.has(child.localName)) {
          paragraph = null;
          wrapper.appendChild(child);
        } else {
          if (!paragraph) { paragraph = out.createElementNS(X, 'p'); wrapper.appendChild(paragraph); }
          paragraph.appendChild(child);
        }
      }
    }
    return wrapper;
  }
  return element;
}
body.appendChild(clone(article, X));
process.stdout.write(JSON.stringify({xhtml: new XMLSerializer().serializeToString(out), mathml4_intents: intents}));
