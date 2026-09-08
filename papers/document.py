"""Preserve ordered scientific XHTML and export reader and Kindle artifacts."""
from __future__ import annotations

import copy
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from native.host import PaperMetadata, validate_epub, write_cover

XHTML = 'http://www.w3.org/1999/xhtml'
MATH = 'http://www.w3.org/1998/Math/MathML'
LTX = 'http://dlmf.nist.gov/LaTeXML'
CSS = '''body {margin: 0; padding: 0;} p {margin: .6em 0;}
h1,h2,h3,h4,h5,h6 {text-align:left; page-break-after:avoid;}
img,svg {max-width:100%; object-fit:contain;} figure {margin:1em 0;}
table {max-width:100%; border-collapse:collapse;} th,td {padding:.2em;}
pre {white-space:pre-wrap; overflow-wrap:anywhere;} a {text-decoration:underline;}
.math-image {display:inline; margin:0; padding:0;}
.display-math {display:block; text-align:center; margin:1em 0;}
.ltx_eqn_table {width:100%;} .ltx_eqn_center_padleft,.ltx_eqn_center_padright {padding:0;}
.ltx_align_center {text-align:center;} .ltx_align_right {text-align:right;}
.ltx_transformed_outer {width:auto!important;height:auto!important;}
.ltx_transformed_inner {transform:none!important;}
.ltx_bibitem {margin:.7em 0;} .ltx_tag_bibitem {margin-right:.5em;}
'''


def local(tag):
    return tag.rsplit('}', 1)[-1]


def xml_bytes(tree):
    ET.register_namespace('', XHTML)
    ET.register_namespace('m', MATH)
    ET.register_namespace('epub', 'http://www.idpf.org/2007/ops')
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True)


def numeric_latexml(data: bytes) -> bytes:
    """Change citation roles before LaTeXML resolves them into rendered prose."""
    tree = ET.fromstring(data)
    for index, item in enumerate(tree.findall('.//{*}bibitem'), 1):
        for tag in item.findall('./{*}tags/{*}tag'):
            if tag.get('role') in {'number', 'refnum'}:
                tag[:] = []
                tag.text = str(index) if tag.get('role') == 'number' else f'[{index}]'
    for cite in tree.findall('.//{*}cite'):
        cls = cite.get('class', '')
        narrative = any(s in cls for s in ('citemacro_citet', 'citemacro_textcite', 'citemacro_Citet'))
        if any(s in cls for s in ('citeauthor', 'citeyear')):
            continue
        for ref in cite.findall('.//{*}bibref'):
            if ref.get('show') == 'nothing':
                continue
            ref.set('separator', ',')
            if narrative:
                ref.set('show', 'Authors Phrase1NumberPhrase2')
                ref[:] = []
                ET.SubElement(ref, f'{{{LTX}}}bibrefphrase').text = '['
                ET.SubElement(ref, f'{{{LTX}}}bibrefphrase').text = ']'
            else:
                ref.set('show', 'Number')
                ref[:] = []
        if not narrative:
            if cite.text and cite.text.startswith('('):
                cite.text = '[' + cite.text[1:]
            elif not (cite.text or '').startswith('['):
                cite.text = '[' + (cite.text or '')
            if len(cite):
                last = cite[-1]
                tail = last.tail or ''
                last.tail = tail[:-1] + ']' if tail.endswith(')') else tail if tail.endswith(']') else tail + ']'
    ET.register_namespace('', LTX)
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True)


def _safe_xhtml(tree):
    """Remove active content while retaining the scientific document."""
    forbidden = {'script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'base'}
    for parent in list(tree.iter()):
        for child in list(parent):
            if local(child.tag) in forbidden:
                if child.tail:
                    if list(parent).index(child):
                        prev = list(parent)[list(parent).index(child) - 1]
                        prev.tail = (prev.tail or '') + child.tail
                    else:
                        parent.text = (parent.text or '') + child.tail
                parent.remove(child)
        for key in list(parent.attrib):
            name = local(key).lower()
            if name.startswith('on') or name in {'srcdoc', 'action', 'formaction'}:
                del parent.attrib[key]
            elif name in {'href', 'src'}:
                value = parent.attrib[key].strip()
                if name == 'href' and value.lower() == 'mailto:' and parent.tag == f'{{{XHTML}}}a':
                    # Some author macros produce an empty mail link around the
                    # displayed address. Preserve the address without a dead link.
                    parent.tag = f'{{{XHTML}}}span'
                    del parent.attrib[key]
                    continue
                scheme = urlsplit(value).scheme.lower()
                if name == 'href' and scheme in {'http', 'https'}:
                    # LaTeXML can retain TeX's escaped underscore in URL targets.
                    parent.attrib[key] = value.replace(r'\_', '_')
                if scheme and scheme not in {'https', 'http', 'mailto'}:
                    raise ValueError('The converted document contains an unsafe resource link.')
                if name == 'src' and scheme:
                    raise ValueError('A paper image was not packaged locally.')
    return tree


def _normalize_structure(tree, repeated_labels=None, warnings=None, table_groups=None, nested_table_groups=None):
    """Remove redundant label markers and make block wrappers valid XHTML."""
    ids = {}
    for element in tree.iter():
        if element.tag == '{http://www.w3.org/1998/Math/MathML}mtable' and element.get('columnspacing') == '':
            # Pandoc emits an invalid empty spacing list for single-column math.
            del element.attrib['columnspacing']
        if element.get('id'):
            ids.setdefault(element.get('id'), []).append(element)
        # LaTeXML wraps resized tables in a span. A div retains the same
        # content and transform while permitting the block-level table.
        if local(element.tag) == 'span' and any(local(c.tag) == 'table' for c in element):
            element.tag = f'{{{XHTML}}}div'
    for identifier, elements in ids.items():
        if len(elements) < 2:
            continue
        markers = [e for e in elements if local(e.tag) == 'span' and e.get('data-label') == identifier and not len(e) and not (e.text or '').strip()]
        targets = [e for e in elements if e not in markers]
        if (nested_table_groups or {}).get(identifier) == len(targets) and len(targets) > 1:
            enclosing = [t for t in targets if all(other in list(t.iter()) for other in targets)]
            captions = [t.find(f'{{{XHTML}}}caption') for t in targets]
            if len(enclosing) == 1 and all(local(t.tag) == 'table' for t in targets) and all(c is not None for c in captions):
                copies = [copy.deepcopy(c) for c in captions]
                for caption in copies:
                    caption.tail = None
                if len({ET.tostring(c) for c in copies}) == 1 and _text(copies[0]):
                    outer = enclosing[0]
                    for target, caption in zip(targets, captions):
                        if target is not outer:
                            del target.attrib['id']
                            target.remove(caption)
                    targets = [outer]
                    if warnings is not None:
                        warnings.append(f'Preserved nested table grids with one shared caption and anchor: {identifier}')
        if (table_groups or {}).get(identifier) == len(targets) and len(targets) > 1:
            # Pandoc duplicates a shared float caption onto each grid. Source
            # structure, matching captions, and sibling order prove this group.
            parents = {child: parent for parent in tree.iter() for child in parent}
            parent = parents.get(targets[0])
            captions = [target.find(f'{{{XHTML}}}caption') for target in targets]
            sibling_tables = parent is not None and all(local(t.tag) == 'table' and parents.get(t) is parent for t in targets)
            if sibling_tables and all(c is not None for c in captions):
                copies = [copy.deepcopy(c) for c in captions]
                for caption in copies:
                    caption.tail = None
                same_caption = len({ET.tostring(c) for c in copies}) == 1
                children = list(parent)
                start, end = children.index(targets[0]), children.index(targets[-1])
                for marker in markers:
                    owner = marker
                    while parents.get(owner) is not None and parents.get(owner) is not parent:
                        owner = parents[owner]
                    if parents.get(owner) is parent and children.index(owner) > end:
                        end = children.index(owner)
                members = children[start:end + 1]
                if same_caption and all(m in targets or local(m.tag) == 'p' for m in members):
                    group = ET.Element(f'{{{XHTML}}}figure', {'id': identifier, 'class': 'table-group'})
                    caption = copies[0]
                    caption.tag = f'{{{XHTML}}}figcaption'
                    group.append(caption)
                    for target, caption in zip(targets, captions):
                        del target.attrib['id']
                        target.remove(caption)
                    for member in members:
                        parent.remove(member)
                        group.append(member)
                    parent.insert(start, group)
                    targets = [group]
                    if warnings is not None:
                        warnings.append(f'Preserved a shared caption and anchor for {len(captions)} table grids: {identifier}')
        if len(targets) != 1:
            # LaTeX's \@newl@bel warns, then overwrites the earlier definition.
            # Match that behavior only for proven repeated source labels on
            # separate elements, never a converter-created enclosing duplicate.
            separate = all(b not in list(a.iter())[1:] for a in targets for b in targets if a is not b)
            if not separate or (repeated_labels or {}).get(identifier, 0) < len(targets):
                raise ValueError(f'The source has ambiguous duplicate link targets: {identifier}')
            for index, target in enumerate(targets[:-1], 1):
                replacement = identifier + f'-duplicate-{index}'
                if replacement in ids:
                    raise ValueError('A repeated source label conflicts with another document anchor.')
                target.set('id', replacement)
            if warnings is not None:
                warnings.append(f'Repeated source label {identifier}: all content retained; references use its final definition, as in LaTeX.')
        for marker in markers:
            del marker.attrib['id']
    def anchor(value):
        return 'anchor-' + hashlib.sha256(value.encode()).hexdigest()[:20] if re.search(r'\s', value) else value
    for element in tree.iter():
        if element.get('id'):
            element.set('id', anchor(element.get('id')))
        href = element.get('href')
        if href and '#' in href and not urlsplit(href).scheme:
            base, fragment = href.split('#', 1)
            element.set('href', base + '#' + anchor(unquote(fragment)))
    return tree


def _text(element):
    # Keep formula source in AI context instead of concatenating mfrac children.
    if local(element.tag) == 'math':
        annotation = element.find('.//{*}annotation[@encoding="application/x-tex"]')
        tex = element.get('alttext') or (annotation.text if annotation is not None else '')
        return f'${tex}$' if tex else ' '.join(''.join(element.itertext()).split())
    element = copy.deepcopy(element)
    for parent in element.iter():
        for child in list(parent):
            if local(child.tag) == 'math':
                annotation = child.find('.//{*}annotation[@encoding="application/x-tex"]')
                tex = child.get('alttext') or (annotation.text if annotation is not None else '')
                replacement = ET.Element(f'{{{XHTML}}}span')
                replacement.text = f' ${tex}$ ' if tex else ' ' + ''.join(child.itertext()) + ' '
                replacement.tail = child.tail
                parent[list(parent).index(child)] = replacement
    return ' '.join(''.join(element.itertext()).split())


def _render_math(formulas, render_cache):
    ET.register_namespace('', MATH)
    keys, pending = [], {}
    for formula in formulas:
        standalone = copy.deepcopy(formula)
        standalone.tail = None
        key = ET.tostring(standalone, encoding='unicode')
        keys.append(key)
        if key not in render_cache:
            pending[key] = {'math': key, 'display': formula.get('display') == 'block'}
    node = shutil.which('node')
    if pending and not node:
        raise ValueError('Install Node.js for Kindle equation rendering.')
    if pending:
        result = subprocess.run([node, str(Path(__file__).with_name('math.js'))],
                                input=json.dumps(list(pending.values())), capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise ValueError('An equation could not be drawn: ' + result.stderr[-500:])
        render_cache.update(zip(pending, json.loads(result.stdout), strict=True))
    return keys


def _math_images(tree, reader: Path, render_cache=None):
    if render_cache is None:
        render_cache = {}
    parents = {child: parent for parent in tree.iter() for child in parent}
    formulas = [e for e in tree.iter() if local(e.tag) == 'math']
    if not formulas:
        return 0
    rsvg = shutil.which('rsvg-convert')
    if not rsvg:
        raise ValueError('Install librsvg for Kindle equation rendering.')
    keys = _render_math(formulas, render_cache)
    for math, key in zip(formulas, keys, strict=True):
        info = render_cache[key]
        digest = hashlib.sha256(('white-background:' + info['svg']).encode()).hexdigest()[:20]
        name = f'math-{digest}.png'
        if not (reader / name).exists():
            if 'png' in info:
                (reader / name).write_bytes(info['png'])
            else:
                subprocess.run([rsvg, '--background-color=white', '--output', str(reader / name)], input=info['svg'].encode(), check=True, capture_output=True, timeout=30)
        if 'png' not in info:
            info['png'] = (reader / name).read_bytes()
        annotation = math.find('.//{*}annotation[@encoding="application/x-tex"]')
        alt = math.get('alttext') or (annotation.text if annotation is not None else '') or _text(math)
        attrs = {'src': name, 'alt': alt, 'class': 'math-image',
                 'style': f'width:{info["width"]:.4f}em;height:{info["height"]:.4f}em;vertical-align:{info["baseline"]:.4f}em;'}
        if math.get('id'):
            attrs['id'] = math.get('id')
        image = ET.Element(f'{{{XHTML}}}img', attrs)
        replacement = image
        if math.get('display') == 'block':
            replacement = ET.Element(f'{{{XHTML}}}span', {'class': 'display-math'})
            replacement.append(image)
        replacement.tail = math.tail
        parent = parents[math]
        parent[list(parent).index(math)] = replacement
    return len(formulas)


def _package(reader: Path, files: dict[str, bytes], metadata: dict, headings: list, output: Path, image_math=False):
    # The compatibility book uses black formula pixels. Do not inherit a
    # converter's automatic dark canvas; opaque images remain legible even
    # when a reader overrides the page theme.
    files['reading.css'] = (CSS + (':root {color-scheme:light;}\n' if image_math else '')).encode()
    title = html.escape(metadata['title'])
    nav_items = ''.join(f'<li><a href="{html.escape(path, quote=True)}">{html.escape(label)}</a></li>' for label, path in headings)
    files['nav.xhtml'] = f'''<html xmlns="{XHTML}" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{nav_items}</ol></nav></body></html>'''.encode()
    files['cover.xhtml'] = f'<html xmlns="{XHTML}"><head><title>{title}</title></head><body><img src="cover.png" alt="{title}" style="width:100%;"/></body></html>'.encode()
    # Every copied file must be declared, including converter CSS and figures.
    manifest = []
    reading = []
    for i, (name, data) in enumerate(files.items()):
        mime = 'application/xhtml+xml' if name.endswith(('.html', '.xhtml')) else mimetypes.guess_type(name)[0] or 'application/octet-stream'
        properties = []
        if name == 'nav.xhtml': properties.append('nav')
        if name == 'cover.png': properties.append('cover-image')
        if mime == 'application/xhtml+xml':
            doc = ET.fromstring(data)
            if any(local(e.tag) == 'math' for e in doc.iter()): properties.append('mathml')
            if any(local(e.tag) == 'svg' for e in doc.iter()): properties.append('svg')
            if name not in {'nav.xhtml', 'cover.xhtml'}: reading.append(f'i{i}')
        prop = f' properties="{" ".join(properties)}"' if properties else ''
        manifest.append(f'<item id="i{i}" href="{html.escape(name, quote=True)}" media-type="{mime}"{prop}/>')
    names = list(files)
    spine = [f'i{names.index("cover.xhtml")}', f'i{names.index("nav.xhtml")}', *reading]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    authors = metadata.get('authors', '').strip()
    creator = f'<dc:creator>{html.escape(authors)}</dc:creator>' if authors else ''
    opf = f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">arxiv:{html.escape(metadata['arxiv_id'])}</dc:identifier><dc:title>{title}</dc:title>{creator}<dc:language>en</dc:language><meta property="dcterms:modified">{now}</meta></metadata><manifest>{''.join(manifest)}</manifest><spine>{''.join(f'<itemref idref="{item}"/>' for item in spine)}</spine><guide><reference type="cover" title="Cover" href="cover.xhtml"/></guide></package>'''
    with zipfile.ZipFile(output, 'w') as book:
        book.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        book.writestr('META-INF/container.xml', '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        book.writestr('EPUB/content.opf', opf, compress_type=zipfile.ZIP_DEFLATED)
        for name, data in files.items():
            book.writestr('EPUB/' + name, data, compress_type=zipfile.ZIP_DEFLATED)
    validate_epub(output, require_png_cover=True)
    if not shutil.which('epubcheck'):
        raise ValueError('Install EPUBCheck to validate the exported book.')
    # Java's image reader otherwise uses the system temp directory, which the
    # conversion sandbox deliberately cannot write.
    environment = {**os.environ, 'JAVA_TOOL_OPTIONS': '-Djava.io.tmpdir="' + str(output.parent.resolve()) + '"'}
    check = subprocess.run(['epubcheck', str(output)], env=environment, capture_output=True, text=True, timeout=120)
    output.with_suffix('.epubcheck.log').write_text(check.stdout + check.stderr)
    if check.returncode:
        raise ValueError('EPUB validation failed: ' + (check.stdout + check.stderr)[-1800:])


def _readable_internal_reference_labels(trees):
    """Replace exposed equation keys only when their live targets prove the type."""
    targets = {(name, e.get('id')): e for name, tree in trees.items()
               for e in tree.iter() if e.get('id')}
    for name, tree in trees.items():
        parents = {child: parent for parent in tree.iter() for child in parent}
        for link in tree.iter():
            if local(link.tag) != 'a':
                continue
            href = urlsplit(link.get('href', ''))
            if href.scheme or href.netloc or not href.fragment:
                continue
            target_name = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(href.path))) if href.path else name
            fragment = unquote(href.fragment)
            target = targets.get((target_name, fragment))
            if target is None:
                continue
            text = ''.join(link.itertext()).strip()
            raw_equation = text == '[' + fragment + ']' and (
                local(target.tag) == 'math' or
                (local(target.tag) in {'div','span','p','table'} and
                 any(local(e.tag) == 'math' and e.get('display') == 'block' for e in target.iter())
                 and not any(re.fullmatch(r'h[1-6]', local(e.tag)) for e in target.iter())))
            algorithm = text.startswith('Algorithm:') and 'Algorithm:' in ''.join(target.itertext())
            if not raw_equation and not algorithm:
                continue
            parent = parents.get(link)
            if parent is None:
                continue
            # The prefix can be split over emphasis spans. Trim only the
            # duplicate type word, keeping its spelling as the linked label.
            slots = [(parent, 'text')]
            def append_text(element):
                slots.append((element, 'text'))
                for child in element:
                    append_text(child)
                    slots.append((child, 'tail'))
            for sibling in parent:
                if sibling is link:
                    break
                append_text(sibling)
                slots.append((sibling, 'tail'))
            preceding = ''.join(getattr(e, attr) or '' for e, attr in slots)
            pattern = r'\b(?:Equation|Eq\.?)[\s\u00a0]*$' if raw_equation else r'\bAlgorithm[\s\u00a0]*$'
            prefix = re.search(pattern, preceding, re.IGNORECASE)
            if prefix:
                offset = 0
                for element, attribute in slots:
                    value = getattr(element, attribute) or ''
                    left, right = max(0, prefix.start()-offset), min(len(value), prefix.end()-offset)
                    if left < right:
                        setattr(element, attribute, value[:left] + value[right:])
                    offset += len(value)
            if raw_equation:
                for child in list(link):
                    link.remove(child)
                link.text = prefix.group().strip() if prefix else 'equation'


def build_document(directory: Path, metadata: dict, converter: str, report=None) -> dict:
    reader = directory / 'reader'
    chapters, passages, headings = [], [], []
    trees = {}
    warnings = []
    from native.host import _command_values, _searchable_tex_source, _read_tex_preserving_bytes
    sources = [_searchable_tex_source(_read_tex_preserving_bytes(source)) for source in (directory / 'source').rglob('*.tex')]
    labels = Counter(label for source in sources for label in _command_values(source, 'label'))
    table_groups = {}
    nested_candidates = {}
    for source in sources:
        for table in re.finditer(r'\\begin\{(?P<env>table\*?)\}(?P<body>.*?)\\end\{(?P=env)\}', source, re.DOTALL):
            body = table.group('body')
            keys = _command_values(body, 'label')
            if len(keys) != 1 or len(_command_values(body, 'caption')) != 1:
                continue
            depth, grids, total = 0, 0, 0
            for boundary in re.finditer(r'\\(begin|end)\{tabular\*?\}', body):
                if boundary[1] == 'begin':
                    grids += depth == 0
                    total += 1
                    depth += 1
                else:
                    depth -= 1
            if depth == 0 and grids == 1 and total > 1:
                nested_candidates.setdefault(keys[0], set()).add(total)
            if depth == 0 and grids > 1 and labels[keys[0]] == 1:
                table_groups[keys[0]] = grids
    nested_table_groups = {key: next(iter(counts)) for key, counts in nested_candidates.items() if len(counts) == 1}
    # LaTeXML produces one ordered main document. Imported EPUBs supply spine.json.
    order_file = reader / 'spine.json'
    order = json.loads(order_file.read_text()) if order_file.exists() else [p.name for p in sorted(reader.glob('*.xhtml'))]
    trees = {name: _normalize_structure(_safe_xhtml(ET.fromstring((reader / name).read_bytes())), labels, warnings, table_groups, nested_table_groups) for name in order}
    _readable_internal_reference_labels(trees)
    for name in order:
        path = reader / name
        tree = trees[name]
        for figure in tree.findall('.//{*}figure'):
            if figure.find('.//{*}img') is not None or figure.find('.//{*}svg') is not None:
                continue
            content = copy.deepcopy(figure)
            for parent in content.iter():
                for child in list(parent):
                    if local(child.tag) == 'figcaption':
                        parent.remove(child)
            if not _text(content):
                raise ValueError('A figure lost its content during conversion: ' + (figure.get('id') or name))
        if any('ltx_ERROR' in e.get('class', '') or 'ltx_missing' in e.get('class', '') for e in tree.iter()):
            raise ValueError('The converter reported unresolved paper content. Open the conversion report.')
        head = tree.find(f'{{{XHTML}}}head')
        if head is not None:
            ET.SubElement(head, f'{{{XHTML}}}link', {'rel':'stylesheet','type':'text/css','href':posixpath.relpath('reading.css', posixpath.dirname(name) or '.')})
        section = metadata['title']
        ancestors = {c:p for p in tree.iter() for c in p}
        for e in tree.iter():
            tag = local(e.tag)
            if re.fullmatch(r'h[1-6]', tag):
                section = _text(e)
                anchor = e.get('id') or f'heading-{len(headings)+1}'
                e.set('id', anchor)
                headings.append((section, name + '#' + anchor))
            if tag not in {'p','table','figure','pre','li','math'}:
                continue
            parent = ancestors.get(e)
            nested = False
            while parent is not None:
                if local(parent.tag) in {'p','table','figure','pre','li','math'}:
                    nested = True
                    break
                parent = ancestors.get(parent)
            text = _text(e)
            if nested or not text: continue
            anchor = e.get('id') or f'p{len(passages)+1:05d}'
            e.set('id', anchor)
            passages.append({'id':f'p{len(passages)+1:05d}', 'section':section, 'text':text, 'href':'reader/' + name + '#' + anchor})
        tree.set('lang', 'en')
        tree.set('{http://www.w3.org/XML/1998/namespace}lang', 'en')
        trees[name] = tree
        path.write_bytes(xml_bytes(tree))
        chapters.append({'title':_text(tree.find('.//{*}h1')) if tree.find('.//{*}h1') is not None else metadata['title'], 'path':'reader/' + name})
    if not passages:
        raise ValueError('The converter produced no readable paper content.')
    (reader / 'reading.css').write_text(CSS + '''
html {font-size:18px;} body {padding:1.4em;line-height:1.65;max-width:72ch;margin:0 auto;}
body > section:first-child {margin-top:0;} h1 {margin-top:0;}
''')
    cover_svg = directory / 'cover.svg'
    write_cover(PaperMetadata(metadata['title'], metadata.get('authors',''), metadata['arxiv_id']), cover_svg)
    subprocess.run(['rsvg-convert', '-w', '1200', '-h', '1600', '-o', str(reader / 'cover.png'), str(cover_svg)], check=True, capture_output=True, timeout=30)
    assets = {p.relative_to(reader).as_posix():p.read_bytes() for p in reader.rglob('*') if p.is_file() and p.suffix.lower() in {'.png','.jpg','.jpeg','.gif','.svg','.css','.woff','.woff2','.ttf','.otf'}}
    semantic = {**assets, **{name:xml_bytes(t) for name,t in trees.items()}}
    _package(reader, semantic, metadata, headings or [(metadata['title'],order[0])], directory / 'semantic.epub')
    total_math = 0
    render_cache = {}
    _render_math([e for tree in trees.values() for e in tree.iter() if local(e.tag) == 'math'], render_cache)
    for name, tree in trees.items():
        total_math += _math_images(tree, reader / posixpath.dirname(name), render_cache)
    assets = {p.relative_to(reader).as_posix():p.read_bytes() for p in reader.rglob('*') if p.is_file() and p.suffix.lower() in {'.png','.jpg','.jpeg','.gif','.svg','.css','.woff','.woff2','.ttf','.otf'}}
    kindle = {**assets, **{name:xml_bytes(t) for name,t in trees.items()}}
    _package(reader, kindle, metadata, headings or [(metadata['title'],order[0])], directory / 'paper.epub', image_math=True)
    document = {**metadata, 'converter':converter, 'chapters':chapters, 'passages':passages,
                'report': {**(report or {}), 'checks':['EPUBCheck both profiles', 'local resources and links', 'ordered passages', 'packaged equation images'], 'warnings':warnings, 'equations':total_math, 'distinct_rendered_equations':len(render_cache)}}
    (directory / 'document.json').write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding='utf-8')
    return document


def export_overview(directory: Path, document: dict, overview: dict) -> Path:
    work = directory / 'overview-export'
    reader = work / 'reader'
    reader.mkdir(parents=True, exist_ok=True)
    # Pandoc reads generated Markdown here, never arbitrary TeX from the paper.
    from papers.overview import clean_citations
    text = clean_citations(overview['text'])
    figure_html = {}
    for extension in ('svg', 'png'):
        for old_figure in reader.glob('fig[0-9]*.' + extension):
            old_figure.unlink()
    for figure in overview.get('figures', []):
        identifier = figure.get('id', '')
        if not re.fullmatch(r'fig\d+', identifier):
            raise ValueError('Invalid overview figure identifier.')
        # Older saved overviews may only have a PNG.
        source = (directory / (figure.get('svg') or figure['png'])).resolve()
        if not source.is_relative_to((directory / 'reader' / 'overview-figures').resolve()) or source.suffix not in ('.svg', '.png'):
            raise ValueError('Invalid overview figure path.')
        filename = identifier + source.suffix
        shutil.copyfile(source, reader / filename)
        marker = 'OVERVIEWFIGURE' + identifier.upper()
        text = text.replace('{{figure:' + identifier + '}}', marker)
        figure_html[marker] = '<figure><img src="' + filename + '" alt="' + html.escape(figure.get('alt', ''), quote=True) + '"/><figcaption>' + html.escape(figure.get('caption', '')) + '</figcaption></figure>'
    result = subprocess.run(['pandoc','--from=markdown-raw_html-raw_tex','--to=html5','--mathml'], input=text, text=True, capture_output=True, timeout=30, check=True)
    body = result.stdout
    for marker, rendered in figure_html.items():
        body = body.replace("<p>" + marker + "</p>", rendered)
    title = 'Overview: ' + document['title']
    provenance = overview.get('provenance', {})
    attribution = ' · '.join(str(value) for value in (provenance.get('model'), provenance.get('created_at')) if value)
    attribution = f'<p>{html.escape(attribution)}</p>' if attribution else ''
    (reader / 'main.xhtml').write_text(f'<html xmlns="{XHTML}"><head><title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1><p>Generated explanation of arXiv {html.escape(document["arxiv_id"])}. Read the <a href="https://arxiv.org/abs/{html.escape(document["arxiv_id"], quote=True)}">original paper</a> for the complete evidence.</p>{attribution}{body}</body></html>')
    build_document(work, {**document, 'title':title}, 'overview')
    shutil.copyfile(work / 'paper.epub', directory / 'overview.epub')
    return directory / 'overview.epub'
