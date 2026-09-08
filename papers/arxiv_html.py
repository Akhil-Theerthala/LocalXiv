"""Retain arXiv's rendered article and package it without network access in the worker."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET

from papers.acquire import download

XHTML = 'http://www.w3.org/1999/xhtml'
SVG = 'http://www.w3.org/2000/svg'


def restore_listings(root: ET.Element) -> int:
    """Use arXiv's embedded original code after checking it against the printed listing."""
    count = 0
    for listing in list(root.iter()):
        if 'ltx_listing' not in listing.get('class', '').split():
            continue
        data = [child for child in listing if 'ltx_listing_data' in child.get('class', '').split()]
        lines = [child for child in listing if 'ltx_listingline' in child.get('class', '').split()]
        if len(data) != 1 or not lines or len(listing) != len(lines) + 1:
            continue
        links = data[0].findall('{*}a')
        prefix = 'data:text/plain;base64,'
        if len(links) != 1 or not links[0].get('href', '').startswith(prefix):
            continue
        payload = links[0].get('href')[len(prefix):]
        if len(payload) > 1_400_000:
            raise ValueError('An embedded code listing exceeds the size limit.')
        raw = base64.b64decode(payload, validate=True).decode('utf-8')
        raw_lines = raw.splitlines(keepends=True)
        printed = '\n'.join(''.join(''.join(child.itertext()) for child in line if 'ltx_tag' not in child.get('class', '').split()) for line in lines)
        # LaTeXML typesets code quotes and backticks as typographic quotes.
        comparable = lambda text: re.sub(r'[\s`\'"‘’“”]', '', text)
        if len(raw_lines) != len(lines) or comparable(raw) != comparable(printed):
            raise ValueError('An embedded code download disagrees with its printed listing.')
        listing.tag = '{' + XHTML + '}pre'
        listing.text = None
        for child in list(listing):
            listing.remove(child)
        code = ET.SubElement(listing, '{' + XHTML + '}code')
        for old, text in zip(lines, raw_lines, strict=True):
            line = ET.SubElement(code, '{' + XHTML + '}span')
            line.text = text
            if old.get('id'):
                line.set('id', old.get('id'))
            for child in old.iter():
                if child is not old and child.get('id'):
                    ET.SubElement(line, '{' + XHTML + '}span', {'id': child.get('id')})
        count += 1
    return count


def restore_caption_groups(root: ET.Element) -> list[dict]:
    """Keep captionof output with its adjacent media inside the same container."""
    groups = []
    parents = {child: parent for parent in root.iter() for child in parent}
    for parent in list(root.iter()):
        for figure in list(parent):
            if figure.tag != '{' + XHTML + '}figure' or len(figure) != 1 or figure[0].tag != '{' + XHTML + '}figcaption':
                continue
            classes = figure.get('class', '').split()
            media = {'table'} if 'ltx_table' in classes else {'img', 'svg'} if 'ltx_figure' in classes else set()
            index = list(parent).index(figure)
            if not media:
                continue
            def outside_media(element):
                if element.tag.rsplit('}', 1)[-1] in media:
                    return ''
                return (element.text or '') + ''.join(outside_media(child) + (child.tail or '') for child in element)
            def media_only(element):
                return (element.tag.rsplit('}', 1)[-1] in {'div', 'p', 'span'} and
                        not (element.tail or '').strip() and not outside_media(element).strip() and
                        any(e.tag.rsplit('}', 1)[-1] in media for e in element.iter()))
            owner = parent
            following = False
            if index == 0:
                # arXiv sometimes puts each body and caption in separate,
                # explicitly broken flex rows. Only pair single-column rows.
                owner = parents.get(parent)
                if (len(parent) != 1 or 'ltx_flex_cell' not in parent.get('class', '').split() or
                        owner is None or 'ltx_flex_figure' not in owner.get('class', '').split()):
                    continue
                cells = list(owner)
                position = cells.index(parent)
                def is_break(element):
                    return 'ltx_flex_break' in element.get('class', '').split() and not len(element) and not (element.text or '').strip()
                if (position and not is_break(cells[position - 1])) or (position + 1 < len(cells) and not is_break(cells[position + 1])):
                    continue
                candidates = [i for i in (position - 2, position + 2) if 0 <= i < len(cells)
                              and (i == 0 or is_break(cells[i - 1]))
                              and (i == len(cells) - 1 or is_break(cells[i + 1])) and media_only(cells[i])]
                if len(candidates) != 1:
                    continue
                index = candidates[0] + 1
                following = candidates[0] > position
            previous = owner[index - 1]
            if not media_only(previous):
                continue
            owner.remove(previous)
            figure.insert(len(figure) if following else 0, previous)
            groups.append({'id': figure.get('id'), 'media': sorted(media)})
    return groups


def parse_article(html: str, title: str) -> tuple[ET.Element, dict]:
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js is required to read arXiv HTML.')
    result = subprocess.run([node, str(Path(__file__).with_suffix('.js'))],
                            input=json.dumps({'html': html, 'title': title}),
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError('The arXiv HTML could not be parsed: ' + result.stderr[-800:])
    parsed = json.loads(result.stdout)
    root = ET.fromstring(parsed['xhtml'])
    listings = restore_listings(root)
    groups = restore_caption_groups(root)
    for svg in root.findall('.//{' + SVG + '}svg'):
        _check_svg(svg)
    return root, {'mathml4_intents_retained_in_original_html': parsed['mathml4_intents'], 'verbatim_code_listings': listings, 'caption_groups': groups}


def asset_url(page: str, value: str) -> str:
    url = urljoin(page, value)
    parsed = urlsplit(url)
    expected = urlsplit(page)
    if (parsed.scheme != 'https' or parsed.netloc != 'arxiv.org' or
            not parsed.path.startswith(expected.path + '/') or parsed.query or parsed.fragment or
            any(part in {'.', '..'} for part in unquote(parsed.path).split('/')) or '\\' in unquote(parsed.path)):
        raise ValueError('An HTML figure points outside this exact arXiv version.')
    if Path(parsed.path).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.gif', '.svg'}:
        raise ValueError('The arXiv HTML uses an unsupported figure format.')
    return url


def embedded_raster(value: str) -> bool:
    match = re.fullmatch(r'data:image/(png|jpeg|gif);base64,(.*)', value, re.DOTALL)
    if match is None or len(value) > 27_000_000:
        return False
    try:
        data = base64.b64decode(re.sub(r'\s+', '', match[2]), validate=True)
    except ValueError:
        return False
    signatures = {'png': (b'\x89PNG\r\n\x1a\n',), 'jpeg': (b'\xff\xd8\xff',), 'gif': (b'GIF87a', b'GIF89a')}
    return data.startswith(signatures[match[1]])


def image_suffix(data: bytes) -> str:
    """Return the suffix recognized from image bytes, independent of the URL name."""
    signatures = {'.png': (b'\x89PNG\r\n\x1a\n',),
                  '.jpg': (b'\xff\xd8\xff',),
                  '.gif': (b'GIF87a', b'GIF89a')}
    for suffix, prefixes in signatures.items():
        if data.startswith(prefixes):
            return suffix
    try:
        root = ET.fromstring(data)
        _check_svg(root)
    except (ET.ParseError, UnicodeDecodeError, ValueError):
        pass
    else:
        if root.tag == '{' + SVG + '}svg':
            return '.svg'
    raise ValueError('A retained HTML figure is not a supported image.')


def check_svg(path: Path) -> None:
    _check_svg(ET.fromstring(path.read_bytes()))


def _check_svg(root: ET.Element) -> None:
    if root.tag != '{' + SVG + '}svg':
        raise ValueError('A downloaded SVG figure is not an SVG document.')
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] in {'script', 'iframe', 'object', 'embed'}:
            raise ValueError('An SVG figure contains active content.')
        for key, value in element.attrib.items():
            name = key.rsplit('}', 1)[-1]
            local_image = element.tag == '{' + SVG + '}image' and embedded_raster(value)
            if name.lower().startswith('on') or (name in {'href', 'src'} and not value.startswith('#') and not local_image):
                raise ValueError('An SVG figure contains an external or active resource.')
        css = (element.get('style') or '') + (element.text or '' if element.tag.endswith('}style') else '')
        if '@import' in css.lower() or any(not value.strip(' \"\'').startswith('#') for value in re.findall(r'url\((.*?)\)', css, re.I)):
            raise ValueError('An SVG figure depends on an external stylesheet resource.')


def retrieve(directory: Path, metadata: dict, progress=lambda _: None) -> dict:
    """Download only after local source conversion failed; never delay a successful import."""
    identifier = metadata['arxiv_id']
    if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.\-]*/\d{7})v[1-9]\d*', identifier):
        raise ValueError('HTML recovery requires an exact arXiv version.')
    page = 'https://arxiv.org/html/' + quote(identifier, safe='/')
    cache = directory / 'arxiv-html'
    cache.mkdir(exist_ok=True)
    raw = cache / 'original.html'
    progress('Retrieving arXiv’s rendered article')
    if not raw.exists():
        download(page, raw, 20_000_000)
    html = raw.read_text(encoding='utf-8')
    if 'arXiv:' + identifier not in html:
        raise ValueError('The rendered page does not identify the requested arXiv version.')
    root, details = parse_article(html, metadata['title'])
    records = []
    resources = {}
    for element in root.iter():
        is_object = element.tag == '{' + XHTML + '}object'
        value = element.get('data') if is_object else element.get('src')
        if is_object and not value:
            raise ValueError('An article object has no retrievable image resource.')
        if not value:
            continue
        if is_object and element.get('type') != 'image/svg+xml':
            raise ValueError('The rendered article contains a non-image object.')
        url = asset_url(page, value)
        resources[url] = None
    if len(resources) > 250:
        raise ValueError('The rendered article exceeds the figure-count limit.')
    total = 0
    for index, url in enumerate(resources, 1):
        progress(f'Retaining arXiv figure {index} of {len(resources)}')
        stem = hashlib.sha256(url.encode()).hexdigest()
        path = next((cache / (stem + suffix) for suffix in ('.png', '.jpg', '.jpeg', '.gif', '.svg')
                     if (cache / (stem + suffix)).exists()), cache / (stem + '.download'))
        if not path.exists():
            download(url, path, 20_000_000)
        suffix = image_suffix(path.read_bytes())
        if path.suffix != suffix:
            normalized = path.with_suffix(suffix)
            path.replace(normalized)
            path = normalized
        name = path.name
        total += path.stat().st_size
        if total > 200_000_000:
            raise ValueError('The rendered article exceeds the total figure-size limit.')
        if path.suffix == '.svg':
            check_svg(path)
        records.append({'url': url, 'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {'url': page, 'html_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
                'assets': records, **details}
    (cache / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def prepare(directory: Path, attempt: Path, metadata: dict) -> dict:
    """Validate cached bytes and turn only verified image objects into local images."""
    # arXiv's renderer can silently truncate slash-form siunitx denominators.
    # The source reader handles them; this HTML route needs independent evidence
    # before accepting that construct. Inspect the source retained by its attempt.
    from native import host
    source = directory / 'pandoc' / 'source'
    source_units_checked = source.is_dir()
    for path in source.rglob('*.tex') if source_units_checked else ():
        text = host._searchable_tex_source(host._read_tex_preserving_bytes(path))
        for match in re.finditer(host._TEX_COMMAND_PREFIX + r'(SI|qty|si|unit)(?![A-Za-z@])', text):
            position = host._skip_tex_trivia(text, match.end())
            if text[position:position + 1] == '[':
                option = host._bracketed_argument(text, position)
                if option is None:
                    continue
                position = host._skip_tex_trivia(text, option[1] + 1)
            argument = host._braced_argument(text, position)
            if argument and match[1] in ('SI', 'qty'):
                argument = host._braced_argument(text, host._skip_tex_trivia(text, argument[1] + 1))
            if argument and '/' in text[argument[0]:argument[1]]:
                raise ValueError('arXiv HTML cannot verify slash-form siunitx denominators. Use a validated source conversion or the original PDF.')
    cache = directory / 'arxiv-html'
    manifest = json.loads((cache / 'manifest.json').read_text())
    if manifest['url'] != 'https://arxiv.org/html/' + quote(metadata['arxiv_id'], safe='/'):
        raise ValueError('The retained HTML belongs to a different paper version.')
    raw = cache / 'original.html'
    if hashlib.sha256(raw.read_bytes()).hexdigest() != manifest['html_sha256']:
        raise ValueError('The retained arXiv HTML changed after retrieval.')
    root, details = parse_article(raw.read_text(encoding='utf-8'), metadata['title'])
    reader = attempt / 'reader'
    reader.mkdir()
    assets = {}
    for record in manifest['assets']:
        name = record['file']
        if Path(name).name != name:
            raise ValueError('An HTML figure has an unsafe local path.')
        source = cache / name
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('A retained HTML figure changed after retrieval.')
        normalized = Path(name).with_suffix(image_suffix(data)).name
        shutil.copyfile(source, reader / normalized)
        assets[record['url']] = normalized
    for element in root.iter():
        is_object = element.tag == '{' + XHTML + '}object'
        value = element.get('data') if is_object else element.get('src')
        if is_object and not value:
            raise ValueError('An article object has no retrievable image resource.')
        if not value:
            continue
        url = asset_url(manifest['url'], value)
        if url not in assets:
            raise ValueError('A figure is missing from the retained HTML.')
        if is_object:
            if element.get('type') != 'image/svg+xml' or len(element):
                raise ValueError('An image object has additional content that needs explicit support.')
            element.tag = '{' + XHTML + '}img'
            del element.attrib['data']
            del element.attrib['type']
            element.set('alt', element.get('alt') or 'Refer to caption')
        element.set('src', assets[url])
    (reader / 'main.xhtml').write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    return {**details, 'url': manifest['url'], 'html_sha256': manifest['html_sha256'], 'figures': len(assets),
            'source_unit_risk_check': 'checked retained source' if source_units_checked else 'source unavailable; not checked'}
